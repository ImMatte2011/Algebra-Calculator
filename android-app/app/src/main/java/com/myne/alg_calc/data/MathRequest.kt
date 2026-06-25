package com.myne.alg_calc.data

import com.google.gson.annotations.SerializedName

/**
 * Questa classe mappa esattamente il modello Pydantic di FastAPI.
 * I campi verranno convertiti automaticamente in JSON dalla libreria Gson.
 */
data class MathRequest(
    @SerializedName("expression") val expression: String,
    @SerializedName("type") val type: String,
    @SerializedName("action") val action: String? = null
)

/**
 * Questa classe serve a ricevere la risposta dal Raspberry Pi.
 */
data class MathResponse(
    @SerializedName("result") val result: String? = null,
    @SerializedName("error") val error: String? = null
)