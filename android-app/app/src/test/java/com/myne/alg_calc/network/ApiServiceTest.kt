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
 * Unit test per ApiService usando MockWebServer.
 *
 * MockWebServer fa partire un vero server HTTP locale in memoria:
 * le richieste vengono davvero fatte, ma verso localhost invece che
 * verso il Raspberry Pi reale. Così testiamo il client HTTP (header,
 * parsing della risposta, gestione errori) senza infrastruttura esterna.
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
    // Token Bearer nell'header
    // -------------------------------------------------------------------------

    @Test
    fun `token non vuoto viene aggiunto all header Authorization`() = runTest {
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
    fun `token vuoto non aggiunge header Authorization`() = runTest {
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
    // Parsing delle risposte
    // -------------------------------------------------------------------------

    @Test
    fun `risposta 200 con result viene parsata correttamente`() = runTest {
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
    fun `risposta 200 con campo error viene parsata correttamente`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"ok":false,"result":null,"error":"Equazione incompleta"}""")
                .setResponseCode(200)
        )

        val response = buildService()
            .solveExpression(MathRequest("x=", "equation"))

        assertNull(response.result)
        assertEquals("Equazione incompleta", response.error)
    }

    // -------------------------------------------------------------------------
    // Gestione errori HTTP
    // -------------------------------------------------------------------------

    @Test(expected = HttpException::class)
    fun `risposta 401 lancia HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Invalid or missing authorization token"}""")
                .setResponseCode(401)
        )

        buildService(token = "token-sbagliato")
            .solveExpression(MathRequest("1+1", "equation"))
    }

    @Test(expected = HttpException::class)
    fun `risposta 403 lancia HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Service is inactive"}""")
                .setResponseCode(403)
        )

        buildService(token = "token-valido")
            .solveExpression(MathRequest("1+1", "equation"))
    }

    @Test(expected = HttpException::class)
    fun `risposta 400 lancia HttpException`() = runTest {
        server.enqueue(
            MockResponse()
                .setBody("""{"detail":"Unable to solve expression"}""")
                .setResponseCode(400)
        )

        buildService().solveExpression(MathRequest("invalida===", "equation"))
    }

    // -------------------------------------------------------------------------
    // Body della richiesta
    // -------------------------------------------------------------------------

    @Test
    fun `body della richiesta contiene expression type e action`() = runTest {
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