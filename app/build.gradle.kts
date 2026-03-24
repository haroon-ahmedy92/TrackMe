plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.kapt)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.hilt.android)
}

fun escapeBuildConfig(value: String): String {
    return value
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
}

val trackmeApiBaseUrl = providers.gradleProperty("TRACKME_API_BASE_URL")
    .orElse("http://10.0.2.2:8000/api/")
val trackmeCommandVerificationPublicKeyPem = providers.gradleProperty("TRACKME_COMMAND_VERIFICATION_PUBLIC_KEY_PEM")
    .orElse("")
val trackmeMapProvider = providers.gradleProperty("TRACKME_MAP_PROVIDER").orElse("google")
val trackmeGoogleStaticMapsApiKey = providers.gradleProperty("TRACKME_GOOGLE_STATIC_MAPS_API_KEY").orElse("")
val trackmeMapboxAccessToken = providers.gradleProperty("TRACKME_MAPBOX_ACCESS_TOKEN").orElse("")
val trackmeMapboxUsername = providers.gradleProperty("TRACKME_MAPBOX_USERNAME").orElse("mapbox")
val trackmeMapboxStyleId = providers.gradleProperty("TRACKME_MAPBOX_STYLE_ID").orElse("streets-v12")

android {
    namespace = "com.example.trackme"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.trackme"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "TRACKME_API_BASE_URL", "\"${escapeBuildConfig(trackmeApiBaseUrl.get())}\"")
        buildConfigField(
            "String",
            "TRACKME_COMMAND_VERIFICATION_PUBLIC_KEY_PEM",
            "\"${escapeBuildConfig(trackmeCommandVerificationPublicKeyPem.get())}\""
        )
        buildConfigField("String", "TRACKME_MAP_PROVIDER", "\"${escapeBuildConfig(trackmeMapProvider.get())}\"")
        buildConfigField(
            "String",
            "TRACKME_GOOGLE_STATIC_MAPS_API_KEY",
            "\"${escapeBuildConfig(trackmeGoogleStaticMapsApiKey.get())}\""
        )
        buildConfigField(
            "String",
            "TRACKME_MAPBOX_ACCESS_TOKEN",
            "\"${escapeBuildConfig(trackmeMapboxAccessToken.get())}\""
        )
        buildConfigField(
            "String",
            "TRACKME_MAPBOX_USERNAME",
            "\"${escapeBuildConfig(trackmeMapboxUsername.get())}\""
        )
        buildConfigField(
            "String",
            "TRACKME_MAPBOX_STYLE_ID",
            "\"${escapeBuildConfig(trackmeMapboxStyleId.get())}\""
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

kapt {
    correctErrorTypes = true
}

dependencies {

    implementation(libs.androidx.core.ktx)
    implementation(libs.material)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)

    implementation(libs.hilt.android)
    kapt(libs.hilt.android.compiler)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    kapt(libs.androidx.room.compiler)

    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.androidx.hilt.work)
    kapt(libs.androidx.hilt.compiler)

    implementation(libs.play.services.location)
    implementation(libs.androidx.datastore.preferences)

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization.converter)
    implementation(libs.okhttp.logging.interceptor)
    implementation(libs.kotlinx.coroutines.play.services)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.firebase.messaging)

    debugImplementation(platform(libs.androidx.compose.bom))
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}
