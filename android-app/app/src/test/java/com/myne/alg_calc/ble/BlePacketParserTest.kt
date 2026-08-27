package com.myne.alg_calc.ble

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Unit tests for BlePacketParser.
 *
 * BlePacketParser parses BLE packets sent by the ESP32 (MicroPython),
 * which are the string representation of a Python tuple, e.g:
 *   ('x^2-1=0', 'equation', None, None)
 *   ('x>3', 'inequality', None, None)
 *   ('x^2+2x', 'expression', 'simplify', None)
 *
 * The tests cover normal cases, expressions with valid parentheses
 * (sin(x), (x+1)/2), recognized types, and expected exceptions.
 */
class BlePacketParserTest {

    // -------------------------------------------------------------------------
    // Normal cases
    // -------------------------------------------------------------------------

    @Test
    fun `parse simple equation`() {
        val result = BlePacketParser.parse("('x^2-1=0', 'equation', None, None)")
        assertEquals("x^2-1=0", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse linear equation`() {
        val result = BlePacketParser.parse("('2*x+3=7', 'equation', None, None)")
        assertEquals("2*x+3=7", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse inequality gt`() {
        val result = BlePacketParser.parse("('x>1', 'inequality', None, None)")
        assertEquals("x>1", result.expression)
        // "inequality" is normalized for the RPi API
        assertEquals("inequality", result.type)
        assertNull(result.action)
    }

    @Test
    fun `parse inequality gte`() {
        val result = BlePacketParser.parse("('x>=0', 'inequality', None, None)")
        assertEquals("inequality", result.type)
    }

    @Test
    fun `parse already normalized inequality type`() {
        // If firmware sends "inequality" directly, it still works
        val result = BlePacketParser.parse("('x<5', 'inequality', None, None)")
        assertEquals("inequality", result.type)
    }

    @Test
    fun `parse expression with action simplify`() {
        val result = BlePacketParser.parse("('x^2+2*x', 'expression', 'simplify', None)")
        assertEquals("x^2+2*x", result.expression)
        assertEquals("expression", result.type)
        assertEquals("simplify", result.action)
    }

    @Test
    fun `parse expression with action factor`() {
        val result = BlePacketParser.parse("('x^2-1', 'expression', 'factor', None)")
        assertEquals("factor", result.action)
    }

    @Test
    fun `parse expression with action expand`() {
        val result = BlePacketParser.parse("('(x+1)*(x-1)', 'expression', 'expand', None)")
        assertEquals("expand", result.action)
    }

    @Test
    fun `parse expression without action`() {
        val result = BlePacketParser.parse("('x^2+1', 'expression', None, None)")
        assertEquals("x^2+1", result.expression)
        assertEquals("expression", result.type)
        assertNull(result.action)
    }

    // -------------------------------------------------------------------------
    // Expressions with legitimate parentheses (critical case documented in parser)
    // -------------------------------------------------------------------------

    @Test
    fun `parse expression with parentheses inside expression`() {
        // Parentheses in (x+1)/2 should not be confused with tuple delimiters
        val result = BlePacketParser.parse("('(x+1)/2', 'expression', 'simplify', None)")
        assertEquals("(x+1)/2", result.expression)
    }

    @Test
    fun `parse expression with sin function`() {
        val result = BlePacketParser.parse("('sin(x)+1=0', 'equation', None, None)")
        assertEquals("sin(x)+1=0", result.expression)
        assertEquals("equation", result.type)
    }

    @Test
    fun `parse expression with nested parentheses`() {
        val result = BlePacketParser.parse("('((x+1)+(x+2))=10', 'equation', None, None)")
        assertEquals("((x+1)+(x+2))=10", result.expression)
    }

    @Test
    fun `parse expression with double quotes inside single quotes`() {
        // Python uses double quotes if the expression contains a single quote
        val result = BlePacketParser.parse("(\"x+1\", 'equation', None, None)")
        assertEquals("x+1", result.expression)
    }

    // -------------------------------------------------------------------------
    // Format without None (minimum 2-field packet)
    // -------------------------------------------------------------------------

    @Test
    fun `parse packet with only expression and type`() {
        val result = BlePacketParser.parse("('x+1=0', 'equation')")
        assertEquals("x+1=0", result.expression)
        assertEquals("equation", result.type)
        assertNull(result.action)
    }

    // -------------------------------------------------------------------------
    // Type normalization
    // -------------------------------------------------------------------------

    @Test
    fun `equation type case insensitive`() {
        val result = BlePacketParser.parse("('x=1', 'Equation', None, None)")
        assertEquals("equation", result.type)
    }

    @Test
    fun `inequality type case insensitive`() {
        val result = BlePacketParser.parse("('x>0', 'Inequality', None, None)")
        assertEquals("inequality", result.type)
    }

    @Test
    fun `expression type case insensitive`() {
        val result = BlePacketParser.parse("('x^2+1', 'Expression', 'simplify', None)")
        assertEquals("expression", result.type)
        assertEquals("simplify", result.action)
    }

    // -------------------------------------------------------------------------
    // Error cases — must throw BlePacketParseException
    // -------------------------------------------------------------------------

    @Test(expected = BlePacketParseException::class)
    fun `empty packet throws exception`() {
        BlePacketParser.parse("")
    }

    @Test(expected = BlePacketParseException::class)
    fun `packet with only spaces throws exception`() {
        BlePacketParser.parse("   ")
    }

    @Test(expected = BlePacketParseException::class)
    fun `packet with single field throws exception`() {
        BlePacketParser.parse("('x+1=0')")
    }

    @Test(expected = BlePacketParseException::class)
    fun `unknown type throws exception`() {
        BlePacketParser.parse("('x+1', 'unknowntype', None, None)")
    }

    @Test(expected = BlePacketParseException::class)
    fun `empty expression throws exception`() {
        BlePacketParser.parse("('', 'equation', None, None)")
    }
}