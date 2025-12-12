"""Handle chat turn use case with rule-based state machine."""

import re
from typing import Optional

from app.application.dtos.chat import ChatRequest, ChatResponse
from app.application.ports.conversation_state_repository import ConversationStateRepository
from app.application.use_cases.user_messages_es import UserMessagesES
from app.domain.entities.conversation_state import ConversationState


class HandleChatTurnUseCase:
    """Use case for handling chat turns with deterministic rule-based flow."""

    def __init__(self, state_repository: ConversationStateRepository) -> None:
        """
        Initialize handle chat turn use case.

        Args:
            state_repository: Repository for conversation state
        """
        self._state_repository = state_repository

    async def execute(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat turn handling.

        Args:
            request: Chat request DTO

        Returns:
            Chat response DTO
        """
        # Get or create conversation state
        state = await self._state_repository.get(request.session_id)

        # Process message and update state
        self._process_message(request.message, state)

        # Determine next action and generate response
        reply, next_action, suggested_questions = self._generate_response(state)

        # Save updated state
        await self._state_repository.save(state)

        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            next_action=next_action,
            suggested_questions=suggested_questions,
            debug={
                "current_step": state.current_step,
                "need": state.need,
                "budget": state.budget,
                "preferences": state.preferences,
                "financing_interest": state.financing_interest,
                "contact_intent": state.contact_intent,
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
                    state.current_step = "budget"
                    break

        # Extract budget - look for numbers with currency symbols
        if state.budget is None:
            # Look for price mentions (numbers with $, pesos, etc.)
            price_pattern = r"[\$]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)"
            prices = re.findall(price_pattern, message)
            if prices:
                # Take the first price found
                state.budget = prices[0]
                state.current_step = "options"
            # Look for budget keywords in Spanish
            elif any(
                word in message_lower
                for word in ["presupuesto", "precio", "costo", "presupuest", "dinero", "budget", "price", "cost"]
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
                positive_keywords = ["sí", "si", "sí", "interesado", "interesada", "quiero", "necesito", "yes", "interested", "want", "need"]
                negative_keywords = ["no", "contado", "efectivo", "cash", "pay"]
                if any(word in message_lower for word in positive_keywords):
                    state.financing_interest = True
                    state.current_step = "financing"
                elif any(word in message_lower for word in negative_keywords):
                    state.financing_interest = False
                    state.current_step = "next_action"

        # Extract contact intent - handle Spanish keywords
        if state.contact_intent is None:
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
                state.contact_intent = True
                state.current_step = "next_action"
            elif any(word in message_lower for word in ["no listo", "no estoy listo", "después", "más tarde", "tal vez", "not ready", "later", "maybe"]):
                state.contact_intent = False
                state.current_step = "next_action"

    def _generate_response(
        self, state: ConversationState
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

        elif missing_field == "contact_intent":
            if state.financing_interest:
                return (
                    UserMessagesES.ASK_CONTACT_WITH_FINANCING,
                    "ask_contact",
                    UserMessagesES.SUGGESTED_CONTACT_WITH_FINANCING,
                )
            else:
                return (
                    UserMessagesES.ASK_CONTACT_WITHOUT_FINANCING,
                    "ask_contact",
                    UserMessagesES.SUGGESTED_CONTACT_WITHOUT_FINANCING,
                )

        else:
            # All fields collected
            return (
                UserMessagesES.COMPLETE,
                "complete",
                UserMessagesES.SUGGESTED_COMPLETE,
            )

