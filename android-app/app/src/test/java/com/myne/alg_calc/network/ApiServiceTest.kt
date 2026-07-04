package com.myne.alg_calc.network

import com.myne.alg_calc.data.MathRequest
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import retrofit2.HttpException

/**
 * Unit test for ApiService using MockWebServer.
 *
 * MockWebServer starts a real local HTTP server in memory:
 * the requests are actually made, but to localhost instead of
 * the real Raspberry Pi. This lets us test the HTTP client (headers,
 * response parsing, error handling) without external infrastructure.
 */
class ApiServiceTest {

    private lateinit var server: MockWebServer
    private lateinit var apiService: ApiService

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private fun buildService(token: String = "") =
        ApiService.create(baseUrl = server.url("/").toString(), token = token)

    // -------------------------------------------------------------------------
    // Bearer token in the Authorization header
    // -------------------------------------------------------------------------

    @Test
    fun `non-empty token is added to Authorization header`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"result":"result:2","error":null}""")
                .setResponseCode(200)
        )

        buildService(token = "my-secret-token")
            .solveExpression(MathRequest("1+1", "equation"))

        val request = server.takeRequest()
        assertEquals("Bearer my-secret-token", request.getHeader("Authorization"))
    }

    @Test
    fun `empty token does not add Authorization header`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"result":"result:2","error":null}""")
                .setResponseCode(200)
        )

        buildService(token = "")
            .solveExpression(MathRequest("1+1", "equation"))

        val request = server.takeRequest()
        assertNull(request.getHeader("Authorization"))
    }

    // -------------------------------------------------------------------------
    // Response parsing
    // -------------------------------------------------------------------------

    @Test
    fun `200 response with result is parsed correctly`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"ok":true,"result":"result: -1, 1","error":null}""")
                .setResponseCode(200)
        )

        val response = buildService()
            .solveExpression(MathRequest("x^2-1=0", "equation"))

        assertNotNull(response.result)
        assertNull(response.error)
    }

    @Test
    fun `200 response with error field is parsed correctly`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"ok":false,"result":null,"error":"Incomplete equation"}""")
                .setResponseCode(200)
        )

        val response = buildService()
            .solveExpression(MathRequest("x=", "equation"))

        assertNull(response.result)
        assertEquals("Incomplete equation", response.error)
    }

    // -------------------------------------------------------------------------
    // HTTP error handling
    // -------------------------------------------------------------------------

    @Test(expected = HttpException::class)
    fun `401 response throws HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Invalid or missing authorization token"}""")
                .setResponseCode(401)
        )

        buildService(token = "token-sbagliato")
            .solveExpression(MathRequest("1+1", "equation"))
    }

    @Test(expected = HttpException::class)
    fun `403 response throws HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Service is inactive"}""")
                .setResponseCode(403)
        )

        buildService(token = "token-valido")
            .solveExpression(MathRequest("1+1", "equation"))
    }

    @Test(expected = HttpException::class)
    fun `400 response throws HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Unable to solve expression"}""")
                .setResponseCode(400)
        )

        buildService().solveExpression(MathRequest("invalida===", "equation"))
    }

    // -------------------------------------------------------------------------
    // Request body
    // -------------------------------------------------------------------------

    @Test
    fun `request body contains expression type and action`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"result":"result:2x","error":null}""")
                .setResponseCode(200)
        )

        buildService().solveExpression(
            MathRequest(expression = "x^2+x", type = "expression", action = "simplify")
        )

        val request = server.takeRequest()
        val body = request.body.readUtf8()
        assert(body.contains("\"expression\"")) { "Manca il campo expression nel body: $body" }
        assert(body.contains("\"type\"")) { "Manca il campo type nel body: $body" }
        assert(body.contains("\"action\"")) { "Manca il campo action nel body: $body" }
        assertEquals("POST", request.method)
        assertEquals("/solve", request.path)
    }
}