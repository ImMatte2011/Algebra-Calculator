package com.myne.alg_calc.ble

/**
 * Parses a packet received from the ESP32.
 *
 * The ESP32 (MicroPython) sends `str(result)` where `result` is a PYTHON TUPLE, e.g:
 *   ('2*x+5=9', 'equation')
 *   ("sin(x)+1=0", 'equation')
 *   ('x>3', 'inequality', 'simplify')
 *
 * IMPORTANT: you cannot do replace("(", "").replace(")", "").split(",") because:
 *  - the algebraic expression may contain valid parentheses (sin(x), (x+1)/2, etc.)
 *    that must NOT be removed, only the tuple's enclosing parentheses;
 *  - if the expression contains a comma or a quote, Python will put it inside quotes
 *    (possibly double quotes if it contains a single quote), and split(",") would break it incorrectly.
 *
 * This parser respects quoted string context: it ignores commas and parentheses inside
 * quoted strings, just like a Python literal parser.
 */
data class ParsedBlePacket(
    val expression: String,
    /** Normalized for the RPi API: "equation" or "inequality". */
    val type: String,
    val action: String? = null
)

class BlePacketParseException(message: String) : Exception(message)

object BlePacketParser {

    fun parse(raw: String): ParsedBlePacket {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) {
            throw BlePacketParseException("Empty BLE packet")
        }

        val inner = stripOuterParens(trimmed)
        val tokens = splitTopLevel(inner)

        if (tokens.size < 2) {
            throw BlePacketParseException(
                "Malformed packet: expected at least 2 fields (expression, type), found ${tokens.size}. Raw: \"$raw\""
            )
        }

        val expression = unquote(tokens[0])
        val rawType = unquote(tokens[1])
        // Python serializes None as the literal string "None"; treat it as null.
        val action = tokens.getOrNull(2)?.let { unquote(it) }?.takeIf { it.isNotBlank() && !it.equals("None", ignoreCase = false) }

        if (expression.isBlank()) {
            throw BlePacketParseException("Empty expression after parsing. Raw: \"$raw\"")
        }

        val type = when {
            rawType.equals("expression", ignoreCase = true) -> "expression"
            rawType.equals("inequality", ignoreCase = true) -> "inequality"
            rawType.equals("equation", ignoreCase = true) -> "equation"
            else -> throw BlePacketParseException("Unknown type: \"$rawType\". Raw: \"$raw\"")
        }

        return ParsedBlePacket(expression = expression, type = type, action = action)
    }

    private fun stripOuterParens(s: String): String {
        return if (s.startsWith("(") && s.endsWith(")")) {
            s.substring(1, s.length - 1)
        } else {
            // Lenient fallback: if firmware ever sends the packet without outer parens
            s
        }
    }

    /** Splits on top-level commas, ignoring commas inside single/double quotes. */
    private fun splitTopLevel(s: String): List<String> {
        val tokens = mutableListOf<String>()
        val current = StringBuilder()
        var quoteChar: Char? = null
        var i = 0
        while (i < s.length) {
            val c = s[i]
            when {
                quoteChar != null && c == '\\' && i + 1 < s.length -> {
                    // Escaped character inside the string: copy it as-is and skip ahead
                    current.append(c).append(s[i + 1])
                    i++
                }
                quoteChar != null && c == quoteChar -> {
                    quoteChar = null
                    current.append(c)
                }
                quoteChar == null && (c == '\'' || c == '"') -> {
                    quoteChar = c
                    current.append(c)
                }
                quoteChar == null && c == ',' -> {
                    tokens.add(current.toString().trim())
                    current.clear()
                }
                else -> current.append(c)
            }
            i++
        }
        if (current.isNotBlank() || tokens.isNotEmpty()) {
            tokens.add(current.toString().trim())
        }
        return tokens
    }

    /** Removes outer single/double quotes and handles simple escapes. */
    private fun unquote(token: String): String {
        val t = token.trim()
        if (t.length >= 2) {
            val first = t.first()
            val last = t.last()
            if ((first == '\'' && last == '\'') || (first == '"' && last == '"')) {
                val body = t.substring(1, t.length - 1)
                return body
                    .replace("\\$first", first.toString())
                    .replace("\\\\", "\\")
            }
        }
        return t
    }
}
