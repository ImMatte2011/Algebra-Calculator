package com.myne.alg_calc.network

import com.myne.alg_calc.data.MathRequest
import com.myne.alg_calc.data.MathResponse
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

interface ApiService {

    @POST("solve")
    suspend fun solveExpression(@Body request: MathRequest): MathResponse

    companion object {
        /**
         * Crea il client Retrofit verso il server FastAPI.
         *
         * @param baseUrl URL base del server (es. "http://100.89.229.75:8000/" via Tailscale
         *                oppure "https://mio-dominio.duckdns.org/" via Caddy).
         * @param token   Bearer token da inviare nell'header Authorization.
         *                Obbligatorio quando il server gira con ACCESS_MODE=public.
         *                Se vuoto, l'header non viene aggiunto (compatibile con ACCESS_MODE=tailscale).
         */
        fun create(baseUrl: String, token: String = ""): ApiService {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                // BASIC: logga metodo/URL/status ma NON il corpo della risposta,
                // così il token e i risultati non finiscono in chiaro nel Logcat.
                level = HttpLoggingInterceptor.Level.BASIC
            }

            val authInterceptor = Interceptor { chain ->
                val request = if (token.isNotBlank()) {
                    chain.request().newBuilder()
                        .addHeader("Authorization", "Bearer $token")
                        .build()
                } else {
                    chain.request()
                }
                chain.proceed(request)
            }

            val client = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(8, TimeUnit.SECONDS)
                .writeTimeout(8, TimeUnit.SECONDS)
                .addInterceptor(authInterceptor)
                .addInterceptor(loggingInterceptor)
                .build()

            return Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)
        }
    }
}