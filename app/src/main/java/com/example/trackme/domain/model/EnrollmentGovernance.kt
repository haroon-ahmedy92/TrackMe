package com.example.trackme.domain.model

enum class OwnershipType {
    SINGLE_USER,
    ORGANIZATION_OWNED
}

enum class EnrollmentAuthorizationRole {
    OWNER,
    ADMIN,
    SECURITY_OPERATOR
}

enum class PairingMethod {
    ENROLLMENT_TOKEN,
    QR_CODE_URI
}

enum class RegistrationState {
    PENDING_BACKEND_VERIFICATION,
    VERIFIED
}
