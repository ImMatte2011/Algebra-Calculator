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
         * Creates the Retrofit client for the FastAPI server.
         *
         * @param baseUrl Base URL of the server (e.g. "http://100.89.229.75:8000/" via Tailscale
         *                or "https://my-domain.duckdns.org/" via Caddy).
         * @param token   Bearer token to send in the Authorization header.
         *                Required when the server runs with ACCESS_MODE=public.
         *                When empty, the header is not added (compatible with ACCESS_MODE=tailscale).
         */
        fun create(baseUrl: String, token: String = ""): ApiService {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                // BASIC: logs method/URL/status but NOT response body,
                // so the token and results do not appear in clear text in Logcat.
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