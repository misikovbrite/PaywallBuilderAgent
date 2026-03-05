import Foundation

enum FeatureGate {
    static let freeInjectionLimit = 1

    static func canAddInjection(currentCount: Int, isPro: Bool) -> Bool {
        isPro || currentCount < freeInjectionLimit
    }

    static func canAccessWeight(isPro: Bool) -> Bool { isPro }
    static func canAccessHealth(isPro: Bool) -> Bool { isPro }
    static func canExportPDF(isPro: Bool) -> Bool { isPro }
}
