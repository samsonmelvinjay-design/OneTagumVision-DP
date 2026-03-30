package com.onetagumvision.receiptscan

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.zxing.integration.android.IntentIntegrator
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.URL
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var tokenText: TextView
    private lateinit var captureCountText: TextView
    private lateinit var previewImage: ImageView
    private lateinit var captureButton: Button
    private lateinit var uploadButton: Button
    private lateinit var loadingView: View

    private var scannedQrUrl: String? = null
    private var token: String? = null
    private val capturedBitmaps = mutableListOf<Bitmap>()

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            previewCaptureLauncher.launch(null)
        } else {
            showStatus("Camera permission is required to capture receipts.")
        }
    }

    private val previewCaptureLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicturePreview()
    ) { bitmap ->
        if (bitmap == null) {
            showStatus("No image captured.")
            return@registerForActivityResult
        }
        capturedBitmaps.add(bitmap)
        previewImage.setImageBitmap(bitmap)
        uploadButton.isEnabled = token != null
        showStatus("Captured ${capturedBitmaps.size} image(s). Add more or tap Upload Receipt.")
        updateCaptureSummary()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        tokenText = findViewById(R.id.tokenText)
        captureCountText = findViewById(R.id.captureCountText)
        previewImage = findViewById(R.id.previewImage)
        captureButton = findViewById(R.id.captureButton)
        uploadButton = findViewById(R.id.uploadButton)
        loadingView = findViewById(R.id.loadingView)

        findViewById<Button>(R.id.scanButton).setOnClickListener {
            startQrScan()
        }
        captureButton.setOnClickListener {
            captureReceipt()
        }
        uploadButton.setOnClickListener {
            uploadReceipt()
        }

        showStatus("Scan a OneTagumVision receipt QR to start.")
        captureButton.isEnabled = false
        uploadButton.isEnabled = false
        updateCaptureSummary()
    }

    private fun startQrScan() {
        val integrator = IntentIntegrator(this)
        integrator.setDesiredBarcodeFormats(IntentIntegrator.QR_CODE)
        integrator.setPrompt("Scan QR from Budget Monitoring")
        integrator.setBeepEnabled(true)
        integrator.setOrientationLocked(false)
        integrator.initiateScan()
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        val result = IntentIntegrator.parseActivityResult(requestCode, resultCode, data)
        if (result != null) {
            if (result.contents.isNullOrBlank()) {
                showStatus("QR scan canceled.")
            } else {
                handleQr(result.contents)
            }
            return
        }
        super.onActivityResult(requestCode, resultCode, data)
    }

    private fun handleQr(raw: String) {
        try {
            val uri = Uri.parse(raw)
            val qrToken = uri.getQueryParameter("token")
            if (qrToken.isNullOrBlank()) {
                showStatus("Invalid QR: token missing.")
                return
            }
            if (!raw.contains("/finance/receipts/mobile-upload/")) {
                showStatus("This QR is not for receipt upload.")
                return
            }

            scannedQrUrl = raw
            token = qrToken
            capturedBitmaps.clear()
            previewImage.setImageDrawable(null)

            tokenText.text = "Token ready"
            captureButton.isEnabled = true
            uploadButton.isEnabled = false
            showStatus("QR scanned. Capture a receipt image.")
            updateCaptureSummary()
        } catch (_: Exception) {
            showStatus("Unable to read QR URL.")
        }
    }

    private fun captureReceipt() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            previewCaptureLauncher.launch(null)
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun uploadReceipt() {
        val localToken = token
        val bitmaps = capturedBitmaps.toList()
        val sourceQrUrl = scannedQrUrl
        if (localToken.isNullOrBlank() || bitmaps.isEmpty() || sourceQrUrl.isNullOrBlank()) {
            showStatus("Scan QR and capture at least one image first.")
            return
        }

        val uploadUrl = deriveUploadApiUrl(sourceQrUrl)
        val eventUrl = deriveEventApiUrl(sourceQrUrl)
        if (uploadUrl.isNullOrBlank()) {
            showStatus("Could not derive upload API URL from QR.")
            return
        }

        showStatus("Uploading ${bitmaps.size} image(s)...")
        setLoading(true)
        Thread {
            try {
                val bodyBuilder = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("token", localToken)
                bitmaps.forEachIndexed { index, bitmap ->
                    val output = ByteArrayOutputStream()
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 92, output)
                    val bytes = output.toByteArray()
                    bodyBuilder.addFormDataPart(
                        "image",
                        "receipt_${System.currentTimeMillis()}_${index + 1}.jpg",
                        bytes.toRequestBody("image/jpeg".toMediaType())
                    )
                }
                val body = bodyBuilder.build()

                val request = Request.Builder()
                    .url(uploadUrl)
                    .addHeader("Accept", "application/json")
                    .post(body)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val responseText = response.body?.string().orEmpty()
                    val contentType = response.header("Content-Type").orEmpty()
                    if (!response.isSuccessful) {
                        throw RuntimeException("Upload failed (${response.code}): $responseText")
                    }
                    if (!contentType.contains("application/json", ignoreCase = true)) {
                        val sample = responseText.take(180).replace("\n", " ")
                        throw RuntimeException("Server returned non-JSON response: $sample")
                    }

                    val json = JSONObject(responseText)
                    if (!json.optBoolean("success")) {
                        val err = json.optString("error", "Upload failed.")
                        throw RuntimeException(err)
                    }
                }

                reportUploadEvent(eventUrl, localToken, "success", "Uploaded ${bitmaps.size} image(s) from mobile.")

                runOnUiThread {
                    showStatus("Upload successful. ${bitmaps.size} image(s) sent. Return to desktop and save entry.")
                    Toast.makeText(this, "Receipt images uploaded", Toast.LENGTH_SHORT).show()
                    capturedBitmaps.clear()
                    previewImage.setImageDrawable(null)
                    uploadButton.isEnabled = false
                    updateCaptureSummary()
                }
            } catch (e: Exception) {
                reportUploadEvent(eventUrl, localToken, "failure", e.message ?: "Upload failed.")
                runOnUiThread {
                    showStatus(e.message ?: "Upload failed.")
                    Toast.makeText(this, "Upload failed", Toast.LENGTH_SHORT).show()
                }
            } finally {
                runOnUiThread { setLoading(false) }
            }
        }.start()
    }

    private fun deriveUploadApiUrl(rawQrUrl: String): String? {
        return try {
            val parsed = URL(rawQrUrl)
            val cleanPath = parsed.path ?: return null
            val apiPath = when {
                cleanPath.endsWith("/mobile-upload/api/") -> cleanPath
                cleanPath.endsWith("/mobile-upload/") -> "${cleanPath}api/"
                cleanPath.endsWith("/mobile-upload") -> "$cleanPath/api/"
                cleanPath.contains("/mobile-upload/") -> cleanPath.replace("/mobile-upload/", "/mobile-upload/api/")
                cleanPath.contains("/mobile-upload") -> cleanPath.replace("/mobile-upload", "/mobile-upload/api")
                else -> return null
            }
            val portPart = if (parsed.port > 0) ":${parsed.port}" else ""
            "${parsed.protocol}://${parsed.host}$portPart$apiPath"
        } catch (_: Exception) {
            null
        }
    }

    private fun deriveEventApiUrl(rawQrUrl: String): String? {
        return try {
            val parsed = URL(rawQrUrl)
            val cleanPath = parsed.path ?: return null
            val eventPath = when {
                cleanPath.endsWith("/mobile-upload/api/") -> cleanPath.replace("/api/", "/event/")
                cleanPath.endsWith("/mobile-upload/") -> "${cleanPath}event/"
                cleanPath.endsWith("/mobile-upload") -> "$cleanPath/event/"
                cleanPath.contains("/mobile-upload/api/") -> cleanPath.replace("/mobile-upload/api/", "/mobile-upload/event/")
                cleanPath.contains("/mobile-upload/") -> cleanPath.replace("/mobile-upload/", "/mobile-upload/event/")
                else -> return null
            }
            val portPart = if (parsed.port > 0) ":${parsed.port}" else ""
            "${parsed.protocol}://${parsed.host}$portPart$eventPath"
        } catch (_: Exception) {
            null
        }
    }

    private fun reportUploadEvent(eventUrl: String?, token: String, eventType: String, message: String) {
        if (eventUrl.isNullOrBlank()) return
        try {
            val payload = "token=${URLEncoder.encode(token, "UTF-8")}" +
                "&event_type=${URLEncoder.encode(eventType, "UTF-8")}" +
                "&message=${URLEncoder.encode(message, "UTF-8")}"
            val request = Request.Builder()
                .url(eventUrl)
                .addHeader("Accept", "application/json")
                .post(payload.toRequestBody("application/x-www-form-urlencoded".toMediaType()))
                .build()
            httpClient.newCall(request).execute().close()
        } catch (_: Exception) {
        }
    }

    private fun setLoading(loading: Boolean) {
        loadingView.visibility = if (loading) View.VISIBLE else View.GONE
        captureButton.isEnabled = !loading && token != null
        uploadButton.isEnabled = !loading && token != null && capturedBitmaps.isNotEmpty()
    }

    private fun updateCaptureSummary() {
        captureCountText.text = if (capturedBitmaps.isEmpty()) {
            getString(R.string.capture_count_empty)
        } else {
            resources.getQuantityString(R.plurals.capture_count, capturedBitmaps.size, capturedBitmaps.size)
        }
        captureButton.text = if (capturedBitmaps.isEmpty()) {
            getString(R.string.capture_receipt)
        } else {
            getString(R.string.add_another_page)
        }
    }

    private fun showStatus(message: String) {
        statusText.text = message
    }
}
