package com.example.trackme.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import androidx.core.content.ContextCompat
import com.example.trackme.core.Hasher
import com.example.trackme.domain.model.NetworkType
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

data class NetworkContext(
    val networkType: NetworkType,
    val hashedWifiSsid: String? = null,
    val hashedWifiBssid: String? = null
)

interface NetworkContextCollector {
    fun collect(): NetworkContext
}

class AndroidNetworkContextCollector @Inject constructor(
    @ApplicationContext private val context: Context,
    private val connectivityManager: ConnectivityManager,
    private val wifiManager: WifiManager,
    private val hasher: Hasher
) : NetworkContextCollector {

    override fun collect(): NetworkContext {
        val capabilities = connectivityManager.getNetworkCapabilities(connectivityManager.activeNetwork)
        val networkType = capabilities.toNetworkType()

        if (networkType != NetworkType.WIFI || !canReadWifiContext()) {
            return NetworkContext(networkType = networkType)
        }

        val wifiInfo = capabilities?.transportInfo as? WifiInfo
            ?: runCatching {
                @Suppress("DEPRECATION")
                wifiManager.connectionInfo
            }.getOrNull()

        val ssidHash = wifiInfo?.ssid.cleanWifiLabel()?.let(hasher::sha256)
        val bssidHash = wifiInfo?.bssid.cleanWifiLabel()?.let(hasher::sha256)
        return NetworkContext(
            networkType = networkType,
            hashedWifiSsid = ssidHash,
            hashedWifiBssid = bssidHash
        )
    }

    private fun NetworkCapabilities?.toNetworkType(): NetworkType {
        return when {
            this == null -> NetworkType.NONE
            hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> NetworkType.WIFI
            hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> NetworkType.CELLULAR
            hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> NetworkType.ETHERNET
            else -> NetworkType.UNKNOWN
        }
    }

    private fun canReadWifiContext(): Boolean {
        val hasWifiStatePermission = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_WIFI_STATE
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasWifiStatePermission) return false

        val hasFineLocation = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarseLocation = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        return hasFineLocation || hasCoarseLocation
    }

    private fun String?.cleanWifiLabel(): String? {
        val normalized = this
            ?.trim()
            ?.removePrefix("\"")
            ?.removeSuffix("\"")
            ?.takeIf { it.isNotEmpty() }
            ?.takeUnless { it.equals("<unknown ssid>", ignoreCase = true) }
            ?.takeUnless { it.equals("02:00:00:00:00:00", ignoreCase = true) }
        return normalized
    }
}
