import Foundation
import StoreKit
import UIKit
import FirebaseAnalytics

// MARK: - Pro State

enum ProState: String, Codable {
    case notPurchased
    case active
    case inGrace
    case billingRetry
    case expired

    var hasAccess: Bool {
        switch self {
        case .active, .inGrace, .billingRetry:
            return true
        case .notPurchased, .expired:
            return false
        }
    }
}

// MARK: - Purchase Errors

enum PurchaseError: LocalizedError {
    case pending
    case unknown
    case noActiveSubscription
    case verificationFailed
    case userCancelled

    var errorDescription: String? {
        switch self {
        case .pending:
            return "Purchase is pending approval"
        case .unknown:
            return "An unknown error occurred"
        case .noActiveSubscription:
            return "No active subscription found"
        case .verificationFailed:
            return "Purchase verification failed"
        case .userCancelled:
            return "Purchase was cancelled"
        }
    }
}

// MARK: - Subscription Service

@MainActor
final class SubscriptionService: ObservableObject {

    // MARK: Singleton (for legacy callers)

    static let shared = SubscriptionService()

    // MARK: Published State

    @Published private(set) var proState: ProState = .notPurchased
    @Published private(set) var products: [Product] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isPurchasing = false
    @Published private(set) var error: Error?
    @Published private(set) var expirationDate: Date?

    // MARK: Convenience

    var isPro: Bool { proState.hasAccess }

    var weeklyProduct: Product? {
        products.first { $0.id == "com.kovneier.glptracker.weekly" }
    }

    var yearlyProduct: Product? {
        products.first { $0.id == "com.kovneier.glptracker.yearly" }
    }

    // MARK: Private

    private let productIds: Set<String> = [
        "com.kovneier.glptracker.weekly",
        "com.kovneier.glptracker.yearly"
    ]

    private var updateListenerTask: Task<Void, Never>?
    private let cacheKey = "glp1_pro_state"
    private let expirationKey = "glp1_expiration_date"

    // MARK: Init

    init() {
        loadCachedState()
        startTransactionListener()

        Task {
            await initialize()
        }
    }

    deinit {
        updateListenerTask?.cancel()
    }

    // MARK: - Public Methods

    func initialize() async {
        isLoading = true
        defer { isLoading = false }

        do {
            try await loadProducts()
            await refreshSubscriptionStatus()
        } catch {
            self.error = error
            print("Failed to initialize subscription service: \(error)")
        }
    }

    func loadProducts() async throws {
        let storeProducts = try await Product.products(for: productIds)

        self.products = storeProducts.sorted { first, second in
            guard let firstSub = first.subscription,
                  let secondSub = second.subscription else {
                return first.price < second.price
            }
            return periodInMonths(firstSub.subscriptionPeriod) < periodInMonths(secondSub.subscriptionPeriod)
        }
    }

    func purchase(_ product: Product) async throws {
        isPurchasing = true
        error = nil
        defer { isPurchasing = false }

        Analytics.logEvent("glp1_purchase_started", parameters: [
            "plan": product.id
        ])

        do {
            let result = try await product.purchase()

            switch result {
            case .success(let verification):
                let transaction = try checkVerified(verification)
                await transaction.finish()
                await refreshSubscriptionStatus()

                Analytics.logEvent("glp1_purchase_completed", parameters: [
                    "plan": product.id,
                    "price": product.displayPrice
                ])

            case .userCancelled:
                Analytics.logEvent("glp1_purchase_cancelled", parameters: [
                    "plan": product.id
                ])
                throw PurchaseError.userCancelled

            case .pending:
                throw PurchaseError.pending

            @unknown default:
                throw PurchaseError.unknown
            }
        } catch {
            if !(error is PurchaseError) || (error as? PurchaseError) != .userCancelled {
                Analytics.logEvent("glp1_purchase_failed", parameters: [
                    "error": error.localizedDescription
                ])
            }
            self.error = error
            throw error
        }
    }

    func restore() async throws {
        isPurchasing = true
        error = nil
        defer { isPurchasing = false }

        do {
            try await AppStore.sync()

            var hasActiveSubscription = false

            for await result in Transaction.currentEntitlements {
                let transaction = try checkVerified(result)

                if transaction.productType == .autoRenewable,
                   let expDate = transaction.expirationDate,
                   expDate > Date() {
                    hasActiveSubscription = true
                }
            }

            if !hasActiveSubscription {
                Analytics.logEvent("glp1_restore_purchases", parameters: ["success": false])
                throw PurchaseError.noActiveSubscription
            }

            Analytics.logEvent("glp1_restore_purchases", parameters: ["success": true])
            await refreshSubscriptionStatus()
        } catch {
            self.error = error
            throw error
        }
    }

    // Legacy wrapper for callers that used the old API
    func restorePurchases() async {
        do {
            try await restore()
        } catch {
            print("[SubscriptionService] restore error: \(error)")
        }
    }

    // Legacy wrapper for callers that used checkEntitlements
    func checkEntitlements() async {
        await refreshSubscriptionStatus()
    }

    func refreshSubscriptionStatus() async {
        var newState = ProState.notPurchased
        var newExpirationDate: Date?

        for await result in Transaction.currentEntitlements {
            do {
                let transaction = try checkVerified(result)

                guard transaction.productType == .autoRenewable else { continue }

                if transaction.revocationDate != nil { continue }

                if let expDate = transaction.expirationDate {
                    newExpirationDate = expDate

                    if expDate > Date() {
                        newState = .active
                        break
                    } else {
                        newState = .expired
                    }
                }
            } catch {
                print("Failed to verify transaction: \(error)")
            }
        }

        if newState != proState {
            proState = newState
            expirationDate = newExpirationDate
            cacheState()
        }
    }

    func manageSubscriptions() {
        if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene {
            Task {
                do {
                    try await AppStore.showManageSubscriptions(in: windowScene)
                } catch {
                    if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                        await UIApplication.shared.open(url)
                    }
                }
            }
        }
    }

    // MARK: - Debug

    #if DEBUG
    func debugSetPro(_ active: Bool) {
        proState = active ? .active : .notPurchased
    }
    #endif

    // MARK: - Private Helpers

    private func startTransactionListener() {
        updateListenerTask = Task {
            for await result in Transaction.updates {
                do {
                    let transaction = try checkVerified(result)
                    await refreshSubscriptionStatus()
                    await transaction.finish()
                } catch {
                    print("Transaction verification failed: \(error)")
                }
            }
        }
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified(_, let error):
            throw error
        case .verified(let safe):
            return safe
        }
    }

    private func periodInMonths(_ period: Product.SubscriptionPeriod) -> Int {
        switch period.unit {
        case .day: return 0
        case .week: return 0
        case .month: return period.value
        case .year: return period.value * 12
        @unknown default: return 0
        }
    }

    // MARK: - Caching

    private func loadCachedState() {
        if let raw = UserDefaults.standard.string(forKey: cacheKey),
           let cached = ProState(rawValue: raw) {
            proState = cached
        }

        if let cached = UserDefaults.standard.object(forKey: expirationKey) as? Date {
            expirationDate = cached
        }
    }

    private func cacheState() {
        UserDefaults.standard.set(proState.rawValue, forKey: cacheKey)
        UserDefaults.standard.set(expirationDate, forKey: expirationKey)
    }
}
