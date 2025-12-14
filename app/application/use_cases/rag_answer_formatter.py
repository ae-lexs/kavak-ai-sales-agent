"""RAG answer formatter for humanizing knowledge base content."""

import re


class RagAnswerFormatter:
    """Formats RAG-retrieved knowledge base content into human-friendly conversational answers."""

    @staticmethod
    def format(chunks_text: str) -> str:
        """
        Format knowledge base content into a human-friendly conversational answer.

        Removes raw KB artifacts (numbered headings, section titles) and improves
        conversational flow while maintaining strict grounding in retrieved content.

        Args:
            chunks_text: Raw text from retrieved knowledge base chunks

        Returns:
            Formatted Spanish answer ready for chat interface
        """
        if not chunks_text or not chunks_text.strip():
            return chunks_text

        # Step 1: Remove markdown heading markers and horizontal rules
        text = re.sub(r"^#{1,6}\s+", "", chunks_text, flags=re.MULTILINE)
        text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)

        # Step 2: Remove leading numbering patterns (e.g., "2. ", "2.1 ", "2.1.1 ")
        text = re.sub(r"^\d+\.\d*\.?\d*\s+", "", text, flags=re.MULTILINE)

        # Step 3: Remove section titles that are not meaningful to end users
        # These are typically short phrases followed by newlines that look like headers
        lines = text.split("\n")
        cleaned_lines = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Remove common KB section header patterns (even if longer)
            header_patterns = [
                r"^Presencia Nacional$",
                r"^Identidad de Kavak$",
                r"^Beneficios de Comprar o Vender con Kavak$",
                r"^Autos 100% Certificados$",
                r"^Plan de Pagos a Meses$",
                r"^Experiencia Digital de Compra$",
                r"^Periodo de Prueba y Garantía$",
                r"^Aplicación Postventa Kavak$",
                r"^Conclusión$",
            ]

            is_section_header = any(
                re.match(pattern, line_stripped, re.IGNORECASE) for pattern in header_patterns
            )

            # Skip lines that look like section headers:
            # - Very short lines (less than 20 chars) that are followed by content
            # - Lines that are just bold text without context
            # - Lines that match common KB section patterns
            if is_section_header:
                # Skip this header line
                continue
            elif (
                len(line_stripped) < 20
                and i < len(lines) - 1
                and lines[i + 1].strip()
                and not line_stripped.startswith("*")
                and not line_stripped.startswith("-")
                and not re.match(r"^\*\*[^*]+\*\*$", line_stripped)  # Not just bold text
            ):
                # Check if it's a meaningful line (contains useful info) or just a header
                if not RagAnswerFormatter._is_meaningful_line(line_stripped, lines[i + 1 : i + 3]):
                    continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        # Step 4: Clean up bold markers but preserve emphasis for location names
        # Convert **Location Name** to **Location Name** (keep for locations)
        # But remove bold from section headers
        text = re.sub(
            r"\*\*([^*]+)\*\*", r"\1", text
        )  # Remove bold, but we'll add back for locations

        # Step 5: Normalize whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = text.strip()

        # Step 6: Improve conversational flow
        text = RagAnswerFormatter._improve_conversational_flow(text)

        # Step 7: Group related information logically
        text = RagAnswerFormatter._group_related_information(text)

        # Step 8: Handle conclusions gracefully
        text = RagAnswerFormatter._handle_conclusions(text)

        return text.strip()

    @staticmethod
    def _is_meaningful_line(line: str, following_lines: list[str]) -> bool:
        """
        Check if a line is meaningful content or just a section header.

        Args:
            line: Line to check
            following_lines: Next few lines for context

        Returns:
            True if line is meaningful, False if it's just a header
        """
        # Common KB section header patterns
        header_patterns = [
            r"^(Presencia|Identidad|Beneficios|Autos|Plan|Experiencia|Periodo|Aplicación|Conclusión)",
            r"^(Compra|Venta|Proceso|Documentación|Funcionalidades)",
        ]
        if any(re.match(pattern, line, re.IGNORECASE) for pattern in header_patterns):
            # Check if following lines have actual content
            if following_lines and any(
                len(following_line.strip()) > 30 for following_line in following_lines[:2]
            ):
                return False  # It's a header followed by content
        return True

    @staticmethod
    def _improve_conversational_flow(text: str) -> str:
        """
        Improve conversational flow by adding natural sentence starters.

        Args:
            text: Text to improve

        Returns:
            Text with improved conversational flow
        """
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            return text

        # Improve first paragraph to start naturally
        first_para = paragraphs[0]

        # Check if it starts with a natural sentence or needs improvement
        natural_starters = [
            "kavak",
            "actualmente",
            "todos los",
            "kavak ofrece",
            "desde",
            "kavak permite",
            "en ",
        ]

        starts_naturally = any(
            first_para.lower().startswith(starter) for starter in natural_starters
        )

        # For location/sedes queries, ensure natural starter
        if any(
            keyword in first_para.lower()
            for keyword in [
                "sedes",
                "puebla",
                "monterrey",
                "ciudad de méxico",
                "guadalajara",
                "querétaro",
                "cuernavaca",
            ]
        ):
            if (
                not starts_naturally
                and "cuenta con" not in first_para.lower()
                and "presencia" not in first_para.lower()
            ):
                # Check if it already mentions presence
                if (
                    "15 sedes" in first_para.lower()
                    or "centros de inspección" in first_para.lower()
                ):
                    # It's the presence statement, make it natural
                    paragraphs[0] = (
                        f"Kavak tiene presencia en varias ciudades de México. {first_para}"
                    )
                else:
                    # It's location details, add presence context
                    paragraphs[0] = (
                        f"Kavak tiene presencia en varias ciudades de México.\n\n{first_para}"
                    )

        if not starts_naturally and first_para and len(first_para) > 20:
            # Capitalize first letter if needed
            if first_para[0].islower():
                paragraphs[0] = first_para[0].upper() + first_para[1:]

        return "\n\n".join(paragraphs)

    @staticmethod
    def _group_related_information(text: str) -> str:
        """
        Group related information logically (city → locations, location → address → hours).

        Args:
            text: Text to group

        Returns:
            Text with logically grouped information
        """
        # Preserve paragraph structure by splitting on double newlines first
        paragraphs = text.split("\n\n")
        processed_paragraphs = []

        for para in paragraphs:
            if not para.strip():
                continue

            lines = para.split("\n")
            grouped_lines = []
            i = 0
            current_city = None

            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                # Detect city headers (e.g., "Puebla", "Monterrey", "Ciudad de México")
                city_match = re.match(r"^([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)*)$", line)
                if city_match and len(line.split()) <= 3:
                    # Check if next lines contain locations
                    if i + 1 < len(lines) and "Kavak" in lines[i + 1]:
                        current_city = line
                        # Don't add city line yet - we'll add it before locations
                        i += 1
                        continue

                # Detect location patterns: "Kavak [Name]" followed by address
                # Also handle "**Kavak [Name]**" (bold format from KB)
                location_match = re.match(
                    r"^(?:\*\*)?Kavak\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)(?:\*\*)?$", line
                )
                if location_match:
                    # If we have a current city and haven't added it yet, add it now
                    if current_city and (
                        not grouped_lines or not grouped_lines[-1].startswith("En")
                    ):
                        grouped_lines.append(f"En {current_city}, por ejemplo, puedes encontrar:")
                        current_city = None  # Mark as added

                    # This is a location name, group it with following address/hours
                    location_name = location_match.group(1).strip()
                    grouped_lines.append(f"• **{location_name}**")

                    # Collect address and hours
                    address_parts = []
                    j = i + 1
                    while j < len(lines) and j < i + 4:  # Look ahead 3-4 lines
                        next_line = lines[j].strip()
                        if not next_line:
                            j += 1
                            continue
                        # Stop if we hit another location, city, or section
                        if (
                            re.match(r"^(?:\*\*)?Kavak\s+", next_line)
                            or (
                                re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$", next_line)
                                and len(next_line.split()) <= 3
                            )
                            or next_line.startswith("##")
                            or next_line.startswith("---")
                        ):
                            break
                        # Collect address/hours lines
                        if (
                            next_line
                            and not next_line.startswith("*")
                            and not next_line.startswith("-")
                        ):
                            # Check if it's hours (contains "Horario" or time patterns)
                            if "horario" in next_line.lower() or re.search(
                                r"\d{1,2}:\d{2}", next_line
                            ):
                                address_parts.append(next_line)
                            elif re.search(r"[A-Za-z].*,\s*\d{5}", next_line):  # Address pattern
                                address_parts.append(next_line)
                            elif len(next_line) > 20:  # Likely address
                                address_parts.append(next_line)
                        j += 1

                    # Format address and hours together
                    if address_parts:
                        formatted_address = "  " + "\n  ".join(address_parts)
                        grouped_lines.append(formatted_address)

                    i = j
                    continue

                # Regular line - keep as is (but skip if it's a city we're processing)
                if line != current_city:
                    grouped_lines.append(line)
                i += 1

            # Join processed lines for this paragraph
            if grouped_lines:
                processed_paragraphs.append("\n".join(grouped_lines))

        # Join paragraphs with double newlines to preserve structure
        return "\n\n".join(processed_paragraphs)

    @staticmethod
    def _handle_conclusions(text: str) -> str:
        """
        Handle conclusions gracefully - rephrase naturally or omit if not valuable.

        Args:
            text: Text that may contain conclusions

        Returns:
            Text with conclusions handled appropriately
        """
        # Remove abrupt conclusion markers like "Además, conclusión"
        text = re.sub(r"^Además,?\s+conclusión[^\n]*", "", text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r"^Conclusión[^\n]*", "", text, flags=re.MULTILINE | re.IGNORECASE)
        # Also remove "Además," at start of lines if followed by generic conclusion text
        text = re.sub(
            r"^Además,\s+(?:conclusión|Kavak México es un referente)[^\n]*",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # Check for conclusion-like sentences at the end
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            return text

        last_para = paragraphs[-1]

        # Identify conclusion patterns
        conclusion_patterns = [
            r"^Kavak México es un referente",
            r"^Combina tecnología",
            r"^Ya sea para comprar",
            r".*referente.*compra.*venta.*autos",
        ]

        is_conclusion = any(
            re.search(pattern, last_para, re.IGNORECASE) for pattern in conclusion_patterns
        )

        if is_conclusion:
            # Check if conclusion adds value or is just generic
            if len(last_para) < 100 or "referente" in last_para.lower():
                # Generic conclusion - remove it
                paragraphs = paragraphs[:-1]
            else:
                # Rephrase conclusion more naturally - remove generic opening
                last_para = re.sub(r"^Kavak México es un referente[^\n]*\.\s*", "", last_para)
                if last_para and len(last_para.strip()) > 20:
                    paragraphs[-1] = last_para.strip()
                else:
                    paragraphs = paragraphs[:-1]

        return "\n\n".join(paragraphs)
