"""Spanish user-facing messages for the AI Commercial Agent."""


class UserMessagesES:
    """Centralized Spanish user-facing messages."""

    # Initial greeting and need collection
    GREETING_ASK_NEED = (
        "¡Hola! Estoy aquí para ayudarte a encontrar el auto perfecto. "
        "¿Qué tipo de auto estás buscando? Por ejemplo, ¿buscas un auto familiar, "
        "un auto para ciudad, o algo para trabajo?"
    )
    SUGGESTED_NEED = [
        "Necesito un auto familiar",
        "Estoy buscando un auto para ciudad",
        "Necesito un vehículo para trabajo",
    ]

    # Budget collection
    @staticmethod
    def ask_budget(need: str) -> str:
        """Generate budget question based on need."""
        if need:
            return (
                f"¡Excelente! Entiendo que buscas un auto {need}. "
                "¿Cuál es tu rango de presupuesto? Puedes decirme un monto específico o un rango."
            )
        return (
            "¿Cuál es tu rango de presupuesto? Puedes decirme un monto específico o un rango."
        )

    SUGGESTED_BUDGET = [
        "Mi presupuesto es alrededor de $200,000",
        "Estoy buscando algo menor a $150,000",
        "Puedo gastar hasta $300,000",
    ]

    # Preferences collection
    @staticmethod
    def ask_preferences(budget: str) -> str:
        """Generate preferences question based on budget."""
        if budget:
            return (
                f"¡Perfecto! Con un presupuesto de {budget}, tenemos excelentes opciones. "
                "¿Tienes alguna preferencia? Por ejemplo, transmisión automática o manual, "
                "tipo de combustible (gasolina, eléctrico, híbrido), o características específicas?"
            )
        return (
            "¿Tienes alguna preferencia? Por ejemplo, transmisión automática o manual, "
            "tipo de combustible (gasolina, eléctrico, híbrido), o características específicas?"
        )

    SUGGESTED_PREFERENCES = [
        "Prefiero transmisión automática",
        "Me interesan los autos eléctricos",
        "Necesito buen rendimiento de combustible",
    ]

    # Financing interest collection
    ASK_FINANCING = (
        "¡Excelente! Basándome en tus preferencias, puedo recomendarte excelentes opciones. "
        "¿Te gustaría explorar opciones de financiamiento? Ofrecemos planes de pago flexibles "
        "con tasas competitivas."
    )
    SUGGESTED_FINANCING = [
        "Sí, me interesa el financiamiento",
        "No, pagaré de contado",
        "Cuéntame más sobre las opciones de financiamiento",
    ]

    # Contact intent collection (with financing)
    ASK_CONTACT_WITH_FINANCING = (
        "¡Genial! Puedo ayudarte con los detalles de financiamiento. "
        "¿Te gustaría agendar una cita para discutir tus opciones con más detalle, "
        "o prefieres continuar explorando en línea?"
    )
    SUGGESTED_CONTACT_WITH_FINANCING = [
        "Sí, me gustaría agendar una cita",
        "Me gustaría continuar en línea",
        "¿Puedes enviarme más información?",
    ]

    # Contact intent collection (without financing)
    ASK_CONTACT_WITHOUT_FINANCING = (
        "¡Perfecto! ¿Te gustaría agendar una cita para ver los autos, "
        "o prefieres continuar explorando en línea?"
    )
    SUGGESTED_CONTACT_WITHOUT_FINANCING = [
        "Sí, me gustaría agendar una cita",
        "Me gustaría continuar en línea",
        "¿Puedes enviarme más información?",
    ]

    # Completion message
    COMPLETE = (
        "¡Gracias por proporcionar toda la información! Tengo todo lo que necesito. "
        "¿Te gustaría agendar una cita para ver los autos, o tienes alguna otra pregunta?"
    )
    SUGGESTED_COMPLETE = [
        "Agendar una cita",
        "Muéstrame recomendaciones de autos",
        "Tengo más preguntas",
    ]

