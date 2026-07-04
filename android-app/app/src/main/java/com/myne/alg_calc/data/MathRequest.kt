package com.myne.alg_calc.data

import com.google.gson.annotations.SerializedName

/**
 * This class maps exactly to the FastAPI Pydantic model.
 * The fields are automatically converted to JSON by Gson.
 */
data class MathRequest(
    @SerializedName("expression") val expression: String,
    @SerializedName("type") val type: String,
    @SerializedName("action") val action: String? = null
)

/**
 * This class models the response received from the Raspberry Pi.
 */
data class MathResponse(
    @SerializedName("result") val result: String? = null,
    @SerializedName("error") val error: String? = null
)