"""Handle chat turn use case with rule-based state machine."""

import re
from typing import Any, Callable, Optional

from app.application.dtos.car import CarSummary
from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.dtos.lead import Lead
from app.application.ports.car_catalog_repository import CarCatalogRepository
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.ports.lead_repository import LeadRepository
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
        lead_repository: Optional[LeadRepository] = None,
        faq_rag_service: Optional[AnswerFaqWithRag] = None,
        logger: Optional[Callable[[str, str, str, Any], None]] = None,
    ) -> None:
        """
        Initialize handle chat turn use case.

        Args:
            state_repository: Repository for conversation state
            car_catalog_repository: Repository for car catalog
            lead_repository: Optional repository for lead capture
            faq_rag_service: Optional FAQ RAG service for answering FAQ questions
            logger: Optional logger function (session_id, turn_id, component, **kwargs)
        """
        self._state_repository = state_repository
        self._car_catalog_repository = car_catalog_repository
        self._lead_repository = lead_repository
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

        # Check for reset keyword
        message_lower = request.message.lower()
        reset_keywords = ["reset", "reiniciar", "empezar de nuevo", "comenzar de nuevo"]
        if any(keyword in message_lower for keyword in reset_keywords):
            # Delete existing state
            await self._state_repository.delete(request.session_id)
            # Create fresh state and save it
            state = ConversationState(session_id=request.session_id)
            await self._state_repository.save(request.session_id, state)
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                action="reset",
            )
            return ChatResponse(
                session_id=request.session_id,
                reply="¡Perfecto! Hemos reiniciado la conversación. ¿En qué puedo ayudarte hoy?",
                next_action="ask_need",
                suggested_questions=[
                    "Estoy buscando un auto familiar",
                    "Quiero un auto para la ciudad",
                    "Necesito un auto para trabajo",
                ],
                debug={
                    "step": "need",
                    "action": "reset",
                },
            )

        # Get or create conversation state
        state = await self._state_repository.get(request.session_id)
        if state is None:
            state = ConversationState(session_id=request.session_id)
        else:
            step_before = state.step

        # Store lead fields before processing to detect changes
        lead_name_before = state.lead_name
        lead_phone_before = state.lead_phone
        lead_preferred_contact_time_before = state.lead_preferred_contact_time

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

        # Trigger lead capture if user expresses scheduling/purchase intent after completing flow
        message_lower = request.message.lower()
        scheduling_keywords = [
            "sí, agendar",
            "si, agendar",
            "agendar cita",
            "sí quiero",
            "si quiero",
            "quiero agendar",
            "me interesa agendar",
            "me gustaría agendar",
            "me gustaria agendar",
            "sí, me gustaría agendar",
            "si, me gustaria agendar",
        ]
        # Check if user wants to schedule appointment
        wants_appointment = any(keyword in message_lower for keyword in scheduling_keywords)
        # User has seen financing plans if loan_term is set (indicates financing flow completed)
        has_financing_info = state.loan_term is not None

        # Trigger lead capture if user wants appointment and we have financing info
        # (This covers the case where user just saw financing plans and wants to schedule)
        # Also allow if flow is complete or step indicates readiness
        if (
            wants_appointment
            and (
                has_financing_info
                or state.is_complete()
                or state.step in ["next_action", "financing"]
            )
            and state.step not in ["collect_contact_info", "handoff_to_human"]
        ):
            # Force step to collect_contact_info to ensure lead capture starts
            state.step = "collect_contact_info"
            # Load existing lead when transitioning to collect_contact_info
            if self._lead_repository:
                existing_lead = await self._lead_repository.get(request.session_id)
                if existing_lead:
                    # Merge existing lead data into state
                    if existing_lead.name and not state.lead_name:
                        state.lead_name = existing_lead.name
                    if existing_lead.phone and not state.lead_phone:
                        state.lead_phone = existing_lead.phone
                    if (
                        existing_lead.preferred_contact_time
                        and not state.lead_preferred_contact_time
                    ):
                        state.lead_preferred_contact_time = existing_lead.preferred_contact_time
                    self._log(
                        request.session_id,
                        turn_id,
                        "use_case",
                        lead_capture_triggered=True,
                        lead_capture_existing_lead_loaded=True,
                    )

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

        # Load existing lead if any when in next_action step (before processing message)
        # This ensures existing lead data is available when lead capture is triggered
        if state.step == "next_action" and self._lead_repository:
            existing_lead = await self._lead_repository.get(request.session_id)
            if existing_lead:
                # Merge existing lead data into state
                if existing_lead.name and not state.lead_name:
                    state.lead_name = existing_lead.name
                if existing_lead.phone and not state.lead_phone:
                    state.lead_phone = existing_lead.phone
                if existing_lead.preferred_contact_time and not state.lead_preferred_contact_time:
                    state.lead_preferred_contact_time = existing_lead.preferred_contact_time
                self._log(
                    request.session_id,
                    turn_id,
                    "use_case",
                    lead_capture_triggered=True,
                    lead_capture_existing_lead_loaded=True,
                )

        # Determine next action and generate response
        reply, next_action, suggested_questions = self._generate_response(
            state, cars, request.session_id, turn_id
        )

        # Handle lead capture trigger from next_action
        if next_action == "ask_contact_info" and state.step != "collect_contact_info":
            state.step = "collect_contact_info"
            # Load existing lead if any when starting lead capture (if not already loaded)
            if self._lead_repository and not (
                state.lead_name or state.lead_phone or state.lead_preferred_contact_time
            ):
                existing_lead = await self._lead_repository.get(request.session_id)
                if existing_lead:
                    # Merge existing lead data into state
                    if existing_lead.name and not state.lead_name:
                        state.lead_name = existing_lead.name
                    if existing_lead.phone and not state.lead_phone:
                        state.lead_phone = existing_lead.phone
                    if (
                        existing_lead.preferred_contact_time
                        and not state.lead_preferred_contact_time
                    ):
                        state.lead_preferred_contact_time = existing_lead.preferred_contact_time
                    self._log(
                        request.session_id,
                        turn_id,
                        "use_case",
                        lead_capture_triggered=True,
                        lead_capture_existing_lead_loaded=True,
                    )

        # Handle lead capture: save after each field is collected
        if (
            state.step == "collect_contact_info" or state.step == "handoff_to_human"
        ) and self._lead_repository:
            missing_lead_field = state.get_next_missing_lead_field()

            # Detect which field was just collected by comparing before/after
            field_collected = None
            if not lead_name_before and state.lead_name:
                field_collected = "lead_name"
            elif not lead_phone_before and state.lead_phone:
                field_collected = "lead_phone"
            elif not lead_preferred_contact_time_before and state.lead_preferred_contact_time:
                field_collected = "lead_preferred_contact_time"

            # Log lead capture state
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                lead_capture_triggered=True,
                lead_capture_missing_fields=[
                    f
                    for f in ["lead_name", "lead_phone", "lead_preferred_contact_time"]
                    if getattr(state, f, None) is None
                ],
                lead_capture_field_requested=missing_lead_field,
                lead_capture_field_collected=field_collected,
            )

            # Save lead after each field is collected (partial or complete)
            # Also save when transitioning to handoff_to_human to ensure final state is persisted
            if (
                field_collected
                or (state.lead_name or state.lead_phone or state.lead_preferred_contact_time)
                or state.step == "handoff_to_human"
            ):
                # Load existing lead to merge
                existing_lead = await self._lead_repository.get(request.session_id)
                if existing_lead:
                    # Merge: use state values if present, otherwise keep existing
                    lead = Lead(
                        session_id=state.session_id,
                        name=state.lead_name or existing_lead.name,
                        phone=state.lead_phone or existing_lead.phone,
                        preferred_contact_time=state.lead_preferred_contact_time
                        or existing_lead.preferred_contact_time,
                        created_at=existing_lead.created_at,  # Preserve original created_at
                    )
                else:
                    # New lead
                    lead = Lead(
                        session_id=state.session_id,
                        name=state.lead_name,
                        phone=state.lead_phone,
                        preferred_contact_time=state.lead_preferred_contact_time,
                        created_at=state.created_at,
                    )

                await self._lead_repository.save(lead)

                # Log lead save with masked phone
                phone_masked = None
                if lead.phone:
                    if len(lead.phone) > 4:
                        phone_masked = f"***{lead.phone[-4:]}"
                    else:
                        phone_masked = "***"

                self._log(
                    request.session_id,
                    turn_id,
                    "use_case",
                    lead_repository_save_called=True,
                    lead_saved_snapshot={
                        "session_id": lead.session_id,
                        "name": lead.name,
                        "phone": phone_masked,
                        "preferred_contact_time": lead.preferred_contact_time,
                        "is_complete": lead.name is not None
                        and lead.phone is not None
                        and lead.preferred_contact_time is not None,
                    },
                )

        # Log when lead capture is complete
        if state.is_lead_complete() and state.step == "handoff_to_human":
            self._log(
                request.session_id,
                turn_id,
                "use_case",
                lead_capture_complete=True,
                next_action="handoff_to_human",
            )

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
        state.touch()  # Update timestamp

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
                # Validate price is reasonable (at least 50,000 MXN)
                price_str = prices[0].replace(",", "").replace(" ", "")
                try:
                    price_value = float(price_str)
                    if price_value >= 50000:
                        state.budget = prices[0]
                        state.step = "options"
                    else:
                        # Price too low - will show error in response
                        state.budget = "invalid"
                except ValueError:
                    # Invalid price format - will show error in response
                    state.budget = "invalid"
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
                # Validate term is in supported range
                if term in [36, 48, 60, 72]:
                    state.loan_term = term
                else:
                    # Store invalid term to show error in response
                    state.loan_term = term  # Will be validated in response generation

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
        purchase_intent_keywords = [
            "comprar",
            "quiero comprar",
            "me interesa",
            "quiero ver",
            "quiero agendar",
            "comprar",
            "buy",
            "purchase",
            "interested in buying",
        ]
        if any(word in message_lower for word in contact_keywords + purchase_intent_keywords):
            state.step = "next_action"

        # Extract lead information when in lead capture flow
        # Check if we're in lead capture by checking step OR if we have partial lead data
        # (This handles cases where step might not be set yet but we're collecting lead info)
        # Also check if the last question was asking for contact info
        # (indicates we're in lead capture)
        is_lead_capture_flow = (
            state.step in ["next_action", "collect_contact_info", "handoff_to_human"]
            or state.lead_name is not None
            or state.lead_phone is not None
            or state.lead_preferred_contact_time is not None
            or (state.last_question and "datos de contacto" in state.last_question.lower())
        )

        if is_lead_capture_flow:
            # Extract name - look for patterns like "me llamo", "mi nombre es", "soy"
            # Also handle direct name input (e.g., "Juan Pérez") when in lead capture flow
            if state.lead_name is None:
                name_patterns = [
                    r"me llamo\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)",
                    r"mi nombre es\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)",
                    r"soy\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)",
                    r"nombre:\s*([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)",
                    r"name:\s*([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)",
                ]
                name_extracted = False
                for pattern in name_patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        state.lead_name = match.group(1).strip()
                        name_extracted = True
                        break

                # Fallback: if in lead capture flow and no name pattern matched,
                # check if message looks like a name (2-3 words, mostly letters, no numbers)
                # This works for both "next_action" and "collect_contact_info" steps
                if not name_extracted:
                    # Simple heuristic: 2-3 words, each word is letters only, at least one
                    # starts with capital
                    words = message.strip().split()
                    if 2 <= len(words) <= 3:
                        # Check if all words are letters only and at least one starts with capital
                        if all(
                            re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]+$", word) for word in words
                        ) and any(word[0].isupper() for word in words):
                            # Check it's not a phone number or other pattern
                            if not re.search(r"\d", message) and not re.search(
                                r"@|http|www|\.com|\.mx", message, re.IGNORECASE
                            ):
                                state.lead_name = message.strip()
                                name_extracted = True
                                # Ensure step is set to collect_contact_info when we extract a name
                                if state.step == "next_action":
                                    state.step = "collect_contact_info"

            # Extract phone - look for phone patterns (Mexican format: 10 digits,
            # possibly with +52, spaces, dashes)
            # Extract phone if we're in lead capture and name is already set
            # (or if phone pattern matches)
            if state.lead_phone is None and (
                state.lead_name is not None or state.step == "collect_contact_info"
            ):
                phone_patterns = [
                    r"(\+52\s?)?([1-9]\d{9})",  # +52 followed by 10 digits
                    r"(\d{10})",  # 10 consecutive digits
                    r"(\d{3}[\s\-]?\d{3}[\s\-]?\d{4})",  # formatted phone
                    r"tel[ée]fono[:\s]+([\d\+\s\-]+)",
                    r"phone[:\s]+([\d\+\s\-]+)",
                    r"whatsapp[:\s]+([\d\+\s\-]+)",
                    r"wa[:\s]+([\d\+\s\-]+)",
                ]
                for pattern in phone_patterns:
                    match = re.search(pattern, message_lower)
                    if match:
                        # Clean up phone number
                        phone = re.sub(r"[\s\-]", "", match.group(0))
                        if phone.startswith("+"):
                            state.lead_phone = phone
                        elif len(phone) == 10:
                            state.lead_phone = f"+52{phone}"
                        else:
                            state.lead_phone = phone
                        # Ensure step is set to collect_contact_info when we extract a phone
                        if state.step == "next_action":
                            state.step = "collect_contact_info"
                        break

            # Extract preferred contact time
            # Extract time if we're in lead capture and name+phone are already set
            # (or if time pattern matches)
            if state.lead_preferred_contact_time is None and (
                (state.lead_name is not None and state.lead_phone is not None)
                or state.step == "collect_contact_info"
            ):
                time_patterns = [
                    r"(mañana|morning)",
                    r"(tarde|afternoon)",
                    r"(noche|evening|night)",
                    r"(día|day)",
                    r"(\d{1,2}[:\s]?(am|pm|AM|PM))",
                    r"(\d{1,2}:\d{2})",
                ]
                time_keywords = {
                    # Order matters: more specific/preferred times first
                    "tarde": "afternoon",
                    "afternoon": "afternoon",
                    "noche": "evening",
                    "evening": "evening",
                    "night": "evening",
                    "mañana": "morning",
                    "morning": "morning",
                    "día": "anytime",
                    "day": "anytime",
                }
                # Check for keywords, prioritizing later matches (more specific)
                # This handles cases like "Mañana en la tarde" where "tarde" should win
                found_keywords = []
                for keyword, value in time_keywords.items():
                    if keyword in message_lower:
                        found_keywords.append((keyword, value))
                # If multiple keywords found, prefer the one that appears later in the message
                # or prefer afternoon/evening over morning if both present
                if found_keywords:
                    if len(found_keywords) > 1:
                        # Check message positions to see which appears later
                        positions = [(message_lower.find(kw), val) for kw, val in found_keywords]
                        # Sort by position (later = higher index), then by preference
                        positions.sort(
                            key=lambda x: (x[0], -1 if x[1] in ["afternoon", "evening"] else 0)
                        )
                        state.lead_preferred_contact_time = positions[-1][1]
                    else:
                        state.lead_preferred_contact_time = found_keywords[0][1]
                    # Ensure step is set to collect_contact_info when we extract contact time
                    if state.step == "next_action":
                        state.step = "collect_contact_info"
                # If no keyword match, check for time patterns
                if state.lead_preferred_contact_time is None:
                    for pattern in time_patterns:
                        match = re.search(pattern, message_lower)
                        if match:
                            state.lead_preferred_contact_time = match.group(0).strip()
                            # Ensure step is set to collect_contact_info when we
                            # extract contact time
                            if state.step == "next_action":
                                state.step = "collect_contact_info"
                            break

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
        self,
        state: ConversationState,
        cars: Optional[list[CarSummary]] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> tuple[str, str, list[str]]:
        """
        Generate response based on current state.

        Args:
            state: Current conversation state

        Returns:
            Tuple of (reply, next_action, suggested_questions) - all in Spanish
        """
        # Check for lead capture flow first (takes priority over other flows)
        if state.step == "collect_contact_info":
            return self._generate_lead_capture_response(state, session_id, turn_id)

        # Check financing flow validation (before missing fields)
        # Handle financing flow: down payment -> loan term -> show plans
        # Skip financing flow if we're already in lead capture
        if (
            state.financing_interest
            and state.selected_car_price
            and state.step != "collect_contact_info"
            and state.step != "handoff_to_human"
        ):
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
            elif state.loan_term not in [36, 48, 60, 72]:
                # Invalid loan term - show error with allowed terms
                invalid_term = state.loan_term
                # Clear invalid term so we can ask again
                state.loan_term = None
                return (
                    f"Lo siento, el plazo de {invalid_term} meses no está disponible. "
                    "Ofrecemos plazos de 36, 48, 60 o 72 meses. ¿Cuál prefieres?",
                    "ask_loan_term",
                    ["36 meses", "48 meses", "60 meses", "72 meses"],
                )
            else:
                # Calculate and show financing plans
                return self._generate_financing_plans_response(state)

        missing_field = state.get_next_missing_field()

        if missing_field == "need":
            return (
                UserMessagesES.GREETING_ASK_NEED,
                "ask_need",
                UserMessagesES.SUGGESTED_NEED,
            )

        elif missing_field == "budget":
            # Check if budget was invalid
            if state.budget == "invalid":
                # Clear invalid budget so we can ask again
                state.budget = None
                return (
                    "Por favor, proporciona un presupuesto válido. "
                    "El monto mínimo es de $50,000 MXN. ¿Cuál es tu presupuesto?",
                    "ask_budget",
                    [
                        "Mi presupuesto es $200,000",
                        "Mi presupuesto es $300,000",
                        "Mi presupuesto es $500,000",
                    ],
                )
            return (
                UserMessagesES.ask_budget(state.need),
                "ask_budget",
                UserMessagesES.SUGGESTED_BUDGET,
            )

        elif missing_field == "preferences":
            # Check if budget was invalid first
            if state.budget == "invalid":
                # Clear invalid budget so we can ask again
                state.budget = None
                return (
                    "Por favor, proporciona un presupuesto válido. "
                    "El monto mínimo es de $50,000 MXN. ¿Cuál es tu presupuesto?",
                    "ask_budget",
                    [
                        "Mi presupuesto es $200,000",
                        "Mi presupuesto es $300,000",
                        "Mi presupuesto es $500,000",
                    ],
                )
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

        else:
            # All fields collected - check if we need to collect contact info
            if state.step == "collect_contact_info":
                return self._generate_lead_capture_response(state, session_id, turn_id)
            # All fields collected, ask about next action
            return (
                UserMessagesES.COMPLETE,
                "next_action",
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
                "ask_contact_info",
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

    def _generate_lead_capture_response(
        self,
        state: ConversationState,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> tuple[str, str, list[str]]:
        """
        Generate response for lead capture flow.

        Args:
            state: Current conversation state
            session_id: Session identifier for logging
            turn_id: Turn identifier for logging

        Returns:
            Tuple of (reply, next_action, suggested_questions) - all in Spanish
        """
        missing_lead_field = state.get_next_missing_lead_field()

        # Log when a field is requested
        if missing_lead_field and session_id and turn_id:
            self._log(
                session_id,
                turn_id,
                "use_case",
                lead_capture_field_requested=missing_lead_field,
            )

        if missing_lead_field == "lead_name":
            # Set step to collect_contact_info to enable extraction
            state.step = "collect_contact_info"
            return (
                "¡Excelente! Para poder ayudarte mejor, necesito algunos datos de contacto. "
                "¿Cómo te llamas?",
                "collect_contact_info",
                [],
            )
        elif missing_lead_field == "lead_phone":
            state.step = "collect_contact_info"
            return (
                f"Gracias {state.lead_name or ''}. "
                "¿Podrías proporcionarme tu número de teléfono o WhatsApp?",
                "collect_contact_info",
                [],
            )
        elif missing_lead_field == "lead_preferred_contact_time":
            state.step = "collect_contact_info"
            return (
                f"Perfecto {state.lead_name or ''}. "
                "¿En qué horario prefieres que te contactemos? "
                "(mañana, tarde, noche, o cualquier momento)",
                "collect_contact_info",
                ["Mañana", "Tarde", "Noche", "Cualquier momento"],
            )
        else:
            # All lead info collected
            state.step = "handoff_to_human"
            return (
                f"¡Perfecto {state.lead_name or ''}! "
                "Hemos registrado tu información. Un asesor se pondrá en contacto contigo pronto. "
                "Gracias por tu interés en Kavak.",
                "handoff_to_human",
                [],
            )
