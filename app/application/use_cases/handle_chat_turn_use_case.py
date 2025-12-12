"""Handle chat turn use case with rule-based state machine."""

import re
from typing import Any, Callable, Optional

from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag
from app.application.use_cases.calculate_financing_plan import CalculateFinancingPlan
from app.application.use_cases.user_messages_es import UserMessagesES
from app.domain.entities.conversation_state import ConversationState
from app.domain.value_objects.money_mxn import MoneyMXN


class HandleChatTurnUseCase:
    """Use case for handling chat turns with deterministic rule-based flow."""

    def __init__(
        self,
        state_repository: ConversationStateRepository,
        car_catalog_repository: CarCatalogRepository,
        faq_rag_service: Optional[AnswerFaqWithRag] = None,
        logger: Optional[Callable[[str, str, str, Any], None]] = None,
    ) -> None:
        """
        Initialize handle chat turn use case.

        Args:
            state_repository: Repository for conversation state
            car_catalog_repository: Repository for car catalog
            faq_rag_service: Optional FAQ RAG service for answering FAQ questions
            logger: Optional logger function (session_id, turn_id, component, **kwargs)
        """
        self._state_repository = state_repository
        self._car_catalog_repository = car_catalog_repository
        self._financing_calculator = CalculateFinancingPlan()
        self._faq_rag_service = faq_rag_service
        self._logger = logger

    def _log(self, session_id: str, turn_id: str, component: str, **kwargs: Any) -> None:
        """
        Log event if logger is available.

        Args:
            session_id: Session identifier
            turn_id: Turn identifier
            component: Component name
            **kwargs: Additional log fields
        """
        if self._logger:
            self._logger(session_id, turn_id, component, **kwargs)

    async def execute(self, request: ChatRequest, turn_id: Optional[str] = None) -> ChatResponse:
        """
        Execute chat turn handling.

        Args:
            request: Chat request DTO
            turn_id: Optional turn identifier for logging

        Returns:
            Chat response DTO
        """
        turn_id = turn_id or "unknown"
        step_before = None

        # Get or create conversation state
        state = await self._state_repository.get(request.session_id)
        if state is None:
            state = ConversationState(session_id=request.session_id)
        else:
            step_before = state.step

        # Check if this is an FAQ question and route to RAG if so
        if self._is_faq_intent(request.message) and self._faq_rag_service:
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                intent_detected="faq",
            )
            # Execute RAG and log retrieval
            reply, suggested_questions = self._faq_rag_service.execute(request.message)
            # Retrieve chunks for logging if repository is accessible
            try:
                if hasattr(self._faq_rag_service, "_knowledge_base_repository"):
                    chunks = self._faq_rag_service._knowledge_base_repository.retrieve(
                        request.message, top_k=5
                    )
                    self._log(
                        request.session_id,
                        turn_id,
                        "use_case",
                        rag_retrieval_top_score=chunks[0].score if chunks else 0.0,
                        rag_chunks_count=len(chunks),
                    )
            except (AttributeError, Exception):
                # If repository is not accessible (e.g., in mocks), skip detailed logging
                pass
            return ChatResponse(
                session_id=request.session_id,
                reply=reply,
                next_action="continue_conversation",
                suggested_questions=suggested_questions,
                debug={
                    "step": "faq_rag",
                    "intent": "faq",
                },
            )

        # Log commercial flow intent
        self._log(
            request.session_id,
            turn_id,
            "use_case",
            intent_detected="commercial_flow",
        )

        # Process message and update state
        self._process_message(request.message, state)

        # Log missing fields
        missing_field = state.get_next_missing_field()
        if missing_field:
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                missing_fields=[missing_field],
            )

        # If step is "options", search for cars
        cars = []
        if state.step == "options":
            filters = self._build_search_filters(state)
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                catalog_filters=filters,
            )
            cars = await self._car_catalog_repository.search(filters)
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                catalog_results_count=len(cars),
            )
            # Store first car price for financing calculations
            if cars and len(cars) > 0 and not state.selected_car_price:
                state.selected_car_price = cars[0].price_mxn

        # Log flow step transition
        if step_before != state.step:
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                flow_step_before=step_before,
                flow_step_after=state.step,
            )

        # Determine next action and generate response
        reply, next_action, suggested_questions = self._generate_response(state, cars)

        # Log financing calculation if applicable
        if state.financing_interest and state.selected_car_price and state.down_payment:
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                financing_inputs={
                    "car_price": state.selected_car_price,
                    "down_payment": state.down_payment,
                    "loan_term": state.loan_term,
                },
            )

        # Update last_question with the reply
        state.last_question = reply

        # Save updated state
        await self._state_repository.save(request.session_id, state)

        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            next_action=next_action,
            suggested_questions=suggested_questions,
            debug={
                "step": state.step,
                "need": state.need,
                "budget": state.budget,
                "preferences": state.preferences,
                "financing_interest": state.financing_interest,
                "down_payment": state.down_payment,
                "loan_term": state.loan_term,
                "selected_car_price": state.selected_car_price,
                "last_question": state.last_question,
            },
        )

    def _process_message(self, message: str, state: ConversationState) -> None:
        """
        Process user message and extract information.

        Args:
            message: User message (in Spanish)
            state: Conversation state to update
        """
        message_lower = message.lower()

        # Extract need (car type, use case) - handle both Spanish and English keywords
        if state.need is None:
            need_keywords = {
                # Spanish keywords
                "familiar": "family",
                "familia": "family",
                "ciudad": "city",
                "urbano": "city",
                "trabajo": "work",
                "laboral": "work",
                "suv": "suv",
                "sedan": "sedan",
                "sedán": "sedan",
                "compacto": "compact",
                "lujo": "luxury",
                "lujoso": "luxury",
                # English keywords (for flexibility)
                "family": "family",
                "city": "city",
                "work": "work",
                "compact": "compact",
                "luxury": "luxury",
            }
            for keyword, value in need_keywords.items():
                if keyword in message_lower:
                    state.need = value
                    state.step = "budget"
                    break

        # Extract budget - look for numbers with currency symbols
        if state.budget is None:
            # Look for price mentions (numbers with $, pesos, etc.)
            price_pattern = r"[\$]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)"
            prices = re.findall(price_pattern, message)
            if prices:
                # Take the first price found
                state.budget = prices[0]
                state.step = "options"
            # Look for budget keywords in Spanish
            elif any(
                word in message_lower
                for word in [
                    "presupuesto",
                    "precio",
                    "costo",
                    "presupuest",
                    "dinero",
                    "budget",
                    "price",
                    "cost",
                ]
            ):
                # User mentioned budget but didn't specify amount - will ask in response
                pass

        # Extract preferences - handle both Spanish and English
        if state.preferences is None:
            preference_keywords = {
                # Spanish keywords
                "automática": "automatic",
                "automático": "automatic",
                "manual": "manual",
                "eléctrico": "electric",
                "electrico": "electric",
                "híbrido": "hybrid",
                "hibrido": "hybrid",
                "gasolina": "gas",
                "gas": "gas",
                "diésel": "diesel",
                "diesel": "diesel",
                # English keywords
                "automatic": "automatic",
                "electric": "electric",
                "hybrid": "hybrid",
            }
            for keyword, value in preference_keywords.items():
                if keyword in message_lower:
                    state.preferences = value
                    break

        # Extract financing interest - handle Spanish keywords
        if state.financing_interest is None:
            financing_keywords = [
                "financiamiento",
                "financiar",
                "crédito",
                "credito",
                "préstamo",
                "prestamo",
                "pago mensual",
                "mensualidad",
                "financing",
                "finance",
                "loan",
                "credit",
                "monthly payment",
            ]
            if any(word in message_lower for word in financing_keywords):
                positive_keywords = [
                    "sí",
                    "si",
                    "sí",
                    "interesado",
                    "interesada",
                    "quiero",
                    "necesito",
                    "yes",
                    "interested",
                    "want",
                    "need",
                ]
                negative_keywords = ["no", "contado", "efectivo", "cash", "pay"]
                if any(word in message_lower for word in positive_keywords):
                    state.financing_interest = True
                    state.step = "financing"
                elif any(word in message_lower for word in negative_keywords):
                    state.financing_interest = False
                    state.step = "next_action"

        # Extract down payment - handle both amount and percentage
        if state.financing_interest and state.down_payment is None and state.selected_car_price:
            # Look for percentage (e.g., "10%", "20 por ciento")
            percent_pattern = r"(\d+)\s*%|(\d+)\s*por\s*ciento"
            percent_match = re.search(percent_pattern, message_lower)
            if percent_match:
                percent = float(percent_match.group(1) or percent_match.group(2))
                if 10 <= percent <= 100:
                    state.down_payment = f"{percent}%"
            else:
                # Look for amount (numbers with $ or pesos)
                amount_pattern = r"[\$]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)"
                amounts = re.findall(amount_pattern, message)
                if amounts:
                    # Take the first amount found
                    state.down_payment = amounts[0]

        # Extract loan term
        if state.financing_interest and state.loan_term is None:
            term_pattern = r"(\d+)\s*(?:meses|mes|month|months)"
            term_match = re.search(term_pattern, message_lower)
            if term_match:
                term = int(term_match.group(1))
                if term in [36, 48, 60, 72]:
                    state.loan_term = term

        # Update step to next_action if user mentions scheduling/contact
        contact_keywords = [
            "agendar",
            "cita",
            "visita",
            "contacto",
            "llamar",
            "reunir",
            "ver",
            "schedule",
            "appointment",
            "visit",
            "contact",
            "call",
            "meet",
        ]
        if any(word in message_lower for word in contact_keywords):
            state.step = "next_action"

    def _is_faq_intent(self, message: str) -> bool:
        """
        Detect if message is an FAQ intent using keyword matching.

        Args:
            message: User message

        Returns:
            True if FAQ intent is detected, False otherwise
        """
        message_lower = message.lower()

        # FAQ keywords in Spanish and English
        faq_keywords = [
            # Kavak brand
            "kavak",
            # Guarantee/Warranty
            "garantía",
            "garantia",
            "warranty",
            "guarantee",
            # Return policy
            "devolución",
            "devolucion",
            "return",
            "reembolso",
            "refund",
            # Delivery
            "entrega",
            "delivery",
            "envío",
            "envio",
            "shipping",
            # Inspection
            "inspección",
            "inspeccion",
            "inspection",
            "revisión",
            "revision",
            # Certification
            "certificado",
            "certification",
            "certificado",
            # Safety/Security
            "seguridad",
            "security",
            "seguro",
            "safe",
            # Process/How it works
            "cómo funciona",
            "como funciona",
            "how does it work",
            "proceso",
            "process",
            # General FAQ indicators
            "qué es",
            "que es",
            "what is",
            "qué ofrecen",
            "que ofrecen",
            "what do you offer",
        ]

        return any(keyword in message_lower for keyword in faq_keywords)

    def _build_search_filters(self, state: ConversationState) -> dict[str, Any]:
        """
        Build search filters from conversation state.

        Args:
            state: Current conversation state

        Returns:
            Dictionary of search filters
        """
        filters: dict[str, Any] = {}

        if state.need:
            filters["need"] = state.need
        if state.budget:
            # Extract numeric value from budget string
            budget_match = re.search(r"(\d+)", state.budget.replace(",", "").replace("$", ""))
            if budget_match:
                filters["max_price"] = float(budget_match.group(1))
        if state.preferences:
            filters["preferences"] = state.preferences

        return filters

    def _generate_response(
        self, state: ConversationState, cars: Optional[list[CarSummary]] = None
    ) -> tuple[str, str, list[str]]:
        """
        Generate response based on current state.

        Args:
            state: Current conversation state

        Returns:
            Tuple of (reply, next_action, suggested_questions) - all in Spanish
        """
        missing_field = state.get_next_missing_field()

        if missing_field == "need":
            return (
                UserMessagesES.GREETING_ASK_NEED,
                "ask_need",
                UserMessagesES.SUGGESTED_NEED,
            )

        elif missing_field == "budget":
            return (
                UserMessagesES.ask_budget(state.need),
                "ask_budget",
                UserMessagesES.SUGGESTED_BUDGET,
            )

        elif missing_field == "preferences":
            # If we have cars, show them; otherwise ask for preferences
            if cars and len(cars) > 0:
                # Store first car price for financing calculations
                if not state.selected_car_price:
                    state.selected_car_price = cars[0].price_mxn

                car_list = "\n".join(
                    [
                        f"- {car.make} {car.model} {car.year}: ${car.price_mxn:,.0f} MXN ({car.mileage_km:,} km)"  # noqa: E501
                        for car in cars[:3]
                    ]
                )
                reply = (
                    f"¡Perfecto! Basándome en tus preferencias, aquí tienes algunas opciones:\n\n{car_list}\n\n"  # noqa: E501
                    "¿Te gustaría explorar opciones de financiamiento para alguno de estos autos?"
                )
                return (
                    reply,
                    "ask_financing",
                    [
                        "Sí, me interesa el financiamiento",
                        "Quiero ver más opciones",
                        "Tengo más preguntas",
                    ],
                )
            else:
                return (
                    UserMessagesES.ask_preferences(state.budget),
                    "ask_preferences",
                    UserMessagesES.SUGGESTED_PREFERENCES,
                )

        elif missing_field == "financing_interest":
            return (
                UserMessagesES.ASK_FINANCING,
                "ask_financing",
                UserMessagesES.SUGGESTED_FINANCING,
            )

        # Handle financing flow: down payment -> loan term -> show plans
        elif state.financing_interest and state.selected_car_price:
            if state.down_payment is None:
                return (
                    UserMessagesES.ask_down_payment(state.selected_car_price),
                    "ask_down_payment",
                    UserMessagesES.SUGGESTED_DOWN_PAYMENT,
                )
            elif state.loan_term is None:
                return (
                    UserMessagesES.ASK_LOAN_TERM,
                    "ask_loan_term",
                    UserMessagesES.SUGGESTED_LOAN_TERM,
                )
            else:
                # Calculate and show financing plans
                return self._generate_financing_plans_response(state)

        else:
            # All fields collected
            return (
                UserMessagesES.COMPLETE,
                "complete",
                UserMessagesES.SUGGESTED_COMPLETE,
            )

    def _generate_financing_plans_response(
        self, state: ConversationState
    ) -> tuple[str, str, list[str]]:
        """
        Generate financing plans response.

        Args:
            state: Current conversation state

        Returns:
            Tuple of (reply, next_action, suggested_questions)
        """
        if not state.selected_car_price or not state.down_payment:
            return (
                "Necesito más información para calcular el financiamiento.",
                "ask_down_payment",
                UserMessagesES.SUGGESTED_DOWN_PAYMENT,
            )

        # Parse down payment
        car_price = MoneyMXN(state.selected_car_price)
        down_payment_amount: MoneyMXN

        if "%" in state.down_payment:
            # Percentage
            percent = float(state.down_payment.replace("%", "").strip())
            down_payment_amount = car_price * (percent / 100)
        else:
            # Amount
            amount_str = state.down_payment.replace(",", "").replace("$", "").strip()
            down_payment_amount = MoneyMXN(float(amount_str))

        # Calculate plans for 36, 48, 60 months (or use selected term if provided)
        if state.loan_term:
            terms = [state.loan_term]
        else:
            terms = [36, 48, 60]

        try:
            plans = self._financing_calculator.calculate_multiple_plans(
                car_price, down_payment_amount, terms
            )

            if not plans:
                return (
                    "Lo siento, no pude calcular los planes de financiamiento. "
                    "Por favor, verifica el enganche (mínimo 10%).",
                    "ask_down_payment",
                    UserMessagesES.SUGGESTED_DOWN_PAYMENT,
                )

            # Format plans
            plans_text = "\n\n".join(
                [UserMessagesES.format_financing_plan(plan.model_dump()) for plan in plans]
            )

            reply = (
                f"¡Perfecto! Aquí están tus opciones de financiamiento "
                f"(tasa de interés: 10% anual):\n\n{plans_text}\n\n"
                "¿Te gustaría agendar una cita para continuar con el proceso?"
            )

            return (
                reply,
                "complete",
                [
                    "Sí, agendar cita",
                    "Tengo más preguntas",
                    "Ver más opciones",
                ],
            )
        except ValueError as e:
            return (
                f"Lo siento, {str(e)}. Por favor, proporciona un enganche válido.",
                "ask_down_payment",
                UserMessagesES.SUGGESTED_DOWN_PAYMENT,
            )
