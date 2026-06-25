package com.myne.alg_calc.ble

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Unit test per BlePacketParser.
 *
 * BlePacketParser parsa i pacchetti BLE inviati dall'ESP32 (MicroPython),
 * che sono la rappresentazione stringa di una tupla Python, es:
 *   ('x^2-1=0', 'equation', None, None)
 *   ('x>3', 'disequation', None, None)
 *   ('x^2+2x', 'expression', 'simplify', None)
 *
 * I test coprono: i casi normali, le espressioni con parentesi legittime
 * (sin(x), (x+1)/2), i tipi riconosciuti e le eccezioni attese.
 */
class BlePacketParserTest {

    // -------------------------------------------------------------------------
    // Casi normali
    // -------------------------------------------------------------------------

    @Test
    fun `parse semplice equazione`() {
        val result = BlePacketParser.parse("('x^2-1=0', 'equation', None, None)")
        assertEquals("x^2-1=0", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse equazione lineare`() {
        val result = BlePacketParser.parse("('2*x+3=7', 'equation', None, None)")
        assertEquals("2*x+3=7", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse disequazione gt`() {
        val result = BlePacketParser.parse("('x>1', 'disequation', None, None)")
        assertEquals("x>1", result.expression)
        // "disequation" viene normalizzato in "inequality" per l'API del RPi
        assertEquals("inequality", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse disequazione gte`() {
        val result = BlePacketParser.parse("('x>=0', 'disequation', None, None)")
        assertEquals("inequality", result.type)
    }

    @Test
    fun `parse inequality type gia normalizzato`() {
        // Se il firmware mandasse direttamente "inequality" va comunque bene
        val result = BlePacketParser.parse("('x<5', 'inequality', None, None)")
        assertEquals("inequality", result.type)
    }

    @Test
    fun `parse expression con action simplify`() {
        val result = BlePacketParser.parse("('x^2+2*x', 'expression', 'simplify', None)")
        assertEquals("x^2+2*x", result.expression)
        assertEquals("expression", result.type)
        assertEquals("simplify", result.action)
    }

    @Test
    fun `parse expression con action factor`() {
        val result = BlePacketParser.parse("('x^2-1', 'expression', 'factor', None)")
        assertEquals("factor", result.action)
    }

    @Test
    fun `parse expression con action expand`() {
        val result = BlePacketParser.parse("('(x+1)*(x-1)', 'expression', 'expand', None)")
        assertEquals("expand", result.action)
    }

    // -------------------------------------------------------------------------
    // Espressioni con parentesi legittime (caso critico documentato nel parser)
    // -------------------------------------------------------------------------

    @Test
    fun `parse espressione con parentesi nell espressione`() {
        // Le parentesi in (x+1)/2 non devono essere confuse con quelle della tupla
        val result = BlePacketParser.parse("('(x+1)/2', 'expression', 'simplify', None)")
        assertEquals("(x+1)/2", result.expression)
    }

    @Test
    fun `parse espressione con funzione sin`() {
        val result = BlePacketParser.parse("('sin(x)+1=0', 'equation', None, None)")
        assertEquals("sin(x)+1=0", result.expression)
        assertEquals("equation", result.type)
    }

    @Test
    fun `parse espressione con piu parentesi annidate`() {
        val result = BlePacketParser.parse("('((x+1)+(x+2))=10', 'equation', None, None)")
        assertEquals("((x+1)+(x+2))=10", result.expression)
    }

    @Test
    fun `parse espressione con doppi apici dentro singoli`() {
        // Python usa doppi apici se l'espressione contiene un apice singolo
        val result = BlePacketParser.parse("(\"x+1\", 'equation', None, None)")
        assertEquals("x+1", result.expression)
    }

    // -------------------------------------------------------------------------
    // Formato senza None (pacchetto minimo a 2 campi)
    // -------------------------------------------------------------------------

    @Test
    fun `parse pacchetto con solo espressione e tipo`() {
        val result = BlePacketParser.parse("('x+1=0', 'equation')")
        assertEquals("x+1=0", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    // -------------------------------------------------------------------------
    // Normalizzazione tipo
    // -------------------------------------------------------------------------

    @Test
    fun `tipo equation case insensitive`() {
        val result = BlePacketParser.parse("('x=1', 'Equation', None, None)")
        assertEquals("equation", result.type)
    }

    @Test
    fun `tipo disequation case insensitive`() {
        val result = BlePacketParser.parse("('x>0', 'Disequation', None, None)")
        assertEquals("inequality", result.type)
    }

    // -------------------------------------------------------------------------
    // Casi di errore — devono lanciare BlePacketParseException
    // -------------------------------------------------------------------------

    @Test(expected = BlePacketParseException::class)
    fun `pacchetto vuoto lancia eccezione`() {
        BlePacketParser.parse("")
    }

    @Test(expected = BlePacketParseException::class)
    fun `pacchetto con solo spazi lancia eccezione`() {
        BlePacketParser.parse("   ")
    }

    @Test(expected = BlePacketParseException::class)
    fun `pacchetto con un solo campo lancia eccezione`() {
        BlePacketParser.parse("('x+1=0')")
    }

    @Test(expected = BlePacketParseException::class)
    fun `tipo non riconosciuto lancia eccezione`() {
        BlePacketParser.parse("('x+1', 'unknowntype', None, None)")
    }

    @Test(expected = BlePacketParseException::class)
    fun `espressione vuota lancia eccezione`() {
        BlePacketParser.parse("('', 'equation', None, None)")
    }
}