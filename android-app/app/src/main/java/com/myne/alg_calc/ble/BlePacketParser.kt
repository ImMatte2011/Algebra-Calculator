package com.myne.alg_calc.ble

/**
 * Risultato del parsing di un pacchetto ricevuto dall'ESP32.
 *
 * L'ESP32 (MicroPython) invia `str(result)` dove `result` è una TUPLA PYTHON, es:
 *   ('2*x+5=9', 'equation')
 *   ("sin(x)+1=0", 'equation')
 *   ('x>3', 'disequation', 'simplify')
 *
 * IMPORTANTE: non si può fare replace("(", "").replace(")", "").split(",") perché:
 *  - l'espressione algebrica può contenere parentesi legittime (sin(x), (x+1)/2, ecc.)
 *    che NON vanno rimosse, solo quelle "di contorno" della tupla;
 *  - se l'espressione contenesse una virgola o un apice, Python la scriverebbe
 *    correttamente tra virgolette (eventualmente doppie, se contiene un apice singolo),
 *    e split(",") la spezzerebbe nel punto sbagliato.
 *
 * Questo parser rispetta il "contesto tra apici": ignora virgole e parentesi che si
 * trovano dentro una stringa quotata, esattamente come farebbe un parser di letterali Python.
 */
data class ParsedBlePacket(
    val expression: String,
    /** Normalizzato per l'API del RPi: "equation" oppure "inequality". */
    val type: String,
    val action: String? = null
)

class BlePacketParseException(message: String) : Exception(message)

object BlePacketParser {

    fun parse(raw: String): ParsedBlePacket {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) {
            throw BlePacketParseException("Pacchetto BLE vuoto")
        }

        val inner = stripOuterParens(trimmed)
        val tokens = splitTopLevel(inner)

        if (tokens.size < 2) {
            throw BlePacketParseException(
                "Pacchetto malformato: attesi almeno 2 campi (espressione, tipo), trovati ${tokens.size}. Raw: \"$raw\""
            )
        }

        val expression = unquote(tokens[0])
        val rawType = unquote(tokens[1])
        val action = tokens.getOrNull(2)?.let { unquote(it) }?.takeIf { it.isNotBlank() }

        if (expression.isBlank()) {
            throw BlePacketParseException("Espressione vuota dopo il parsing. Raw: \"$raw\"")
        }

        val type = when {
            rawType.contains("disequation", ignoreCase = true) -> "inequality"
            rawType.contains("inequality", ignoreCase = true) -> "inequality"
            rawType.contains("equation", ignoreCase = true) -> "equation"
            else -> throw BlePacketParseException("Tipo non riconosciuto: \"$rawType\". Raw: \"$raw\"")
        }

        return ParsedBlePacket(expression = expression, type = type, action = action)
    }

    private fun stripOuterParens(s: String): String {
        return if (s.startsWith("(") && s.endsWith(")")) {
            s.substring(1, s.length - 1)
        } else {
            // Tollerante: se mai il firmware mandasse il pacchetto senza parentesi esterne
            s
        }
    }

    /** Divide su virgole "di primo livello", ignorando quelle dentro apici singoli/doppi. */
    private fun splitTopLevel(s: String): List<String> {
        val tokens = mutableListOf<String>()
        val current = StringBuilder()
        var quoteChar: Char? = null
        var i = 0
        while (i < s.length) {
            val c = s[i]
            when {
                quoteChar != null && c == '\\' && i + 1 < s.length -> {
                    // Carattere "escaped" dentro la stringa: copialo cosi' com'e' e salta avanti
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

    /** Rimuove gli apici esterni (singoli o doppi) e gestisce gli escape semplici. */
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