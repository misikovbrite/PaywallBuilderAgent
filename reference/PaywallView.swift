import SwiftUI
import StoreKit
import FirebaseAnalytics
import FirebaseRemoteConfig

struct PaywallView: View {
    @EnvironmentObject var subscriptionService: SubscriptionService

    @State private var selectedPlanId = "com.kovneier.glptracker.yearly"
    @State private var showCloseButton = false
    @State private var isPurchasing = false
    @State private var showError = false
    @State private var errorMessage = ""
    @State private var showRestoreAlert = false
    @State private var restoreSuccess = false

    let source: String
    let onComplete: () -> Void

    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    private var isIPad: Bool { horizontalSizeClass == .regular }

    // Theme
    private let accent = Color(red: 0.23, green: 0.51, blue: 0.96)
    private let accentLight = Color(red: 0.43, green: 0.68, blue: 1.0)
    private let primaryText = Color(red: 0.11, green: 0.11, blue: 0.12)
    private let secondaryText = Color(red: 0.53, green: 0.53, blue: 0.55)
    private let cardBg = Color.white
    private let background = Color(red: 0.96, green: 0.97, blue: 0.98)

    // Convenience product accessors
    private var weeklyProduct: Product? {
        subscriptionService.products.first { $0.id == "com.kovneier.glptracker.weekly" }
    }

    private var yearlyProduct: Product? {
        subscriptionService.products.first { $0.id == "com.kovneier.glptracker.yearly" }
    }

    var body: some View {
        ZStack {
            background.ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 0) {
                    Spacer().frame(height: 16)

                    // 1. Title + close button
                    ZStack(alignment: .trailing) {
                        Text("Track Your GLP-1 Journey")
                            .font(.system(size: 26, weight: .bold))
                            .foregroundColor(primaryText)
                            .frame(maxWidth: .infinity)

                        if showCloseButton {
                            Button {
                                Analytics.logEvent("glp1_paywall_dismissed", parameters: ["source": source])
                                onComplete()
                            } label: {
                                Image(systemName: "xmark")
                                    .font(.system(size: 16, weight: .medium))
                                    .foregroundColor(secondaryText.opacity(0.4))
                                    .frame(width: 36, height: 36)
                            }
                            .transition(.opacity)
                        }
                    }
                    .padding(.horizontal, 24)

                    Spacer().frame(height: 20)

                    // 2. Timeline
                    Text("How Your Free Trial Works")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(primaryText)

                    Spacer().frame(height: 14)

                    timelineSection
                        .padding(.horizontal, 40)

                    Spacer().frame(height: 20)

                    // 3. Plan Cards
                    planCardsSection
                        .padding(.horizontal, 24)

                    Spacer().frame(height: 10)

                    // 4. Trial info text
                    trialInfoText

                    Spacer().frame(height: 12)

                    // 5. Money-back guarantee
                    moneyBackBadge
                        .padding(.horizontal, 24)

                    Spacer().frame(height: 50)

                    // 6. Features Section
                    featuresSection

                    Spacer().frame(height: 50)

                    // 7. Reviews carousel
                    reviewsSection

                    Spacer().frame(height: 40)

                    // 8. Features carousel
                    featuresCarouselSection

                    Spacer().frame(height: 40)

                    // 9. Terms section
                    termsSection

                    Spacer().frame(height: 120)
                }
                .frame(maxWidth: isIPad ? 700 : .infinity)
                .frame(maxWidth: .infinity)
            }
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            stickyBottomBar
        }
        .onAppear {
            Analytics.logEvent("glp1_paywall_shown", parameters: ["source": source])

            let remoteConfig = RemoteConfig.remoteConfig()
            let delay = remoteConfig.configValue(forKey: "glp1_close_button_delay").numberValue.doubleValue

            DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                withAnimation(.easeIn(duration: 0.3)) {
                    showCloseButton = true
                }
            }
        }
        .alert("Error", isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage)
        }
        .alert(restoreSuccess ? "Success" : "Not Found", isPresented: $showRestoreAlert) {
            Button("OK", role: .cancel) {
                if restoreSuccess { onComplete() }
            }
        } message: {
            Text(restoreSuccess
                 ? "Your subscription has been restored!"
                 : "No active subscription found. Please subscribe or contact support.")
        }
    }

    // MARK: - Timeline

    private var timelineSection: some View {
        VStack(spacing: 0) {
            timelineStep(
                icon: "checkmark.circle.fill",
                title: "Today",
                description: "Instant full access to all features",
                isFirst: true,
                isLast: false
            )
            timelineStep(
                icon: "lock.open.fill",
                title: "Full Access",
                description: "Track injections, weight, and side effects",
                isFirst: false,
                isLast: false
            )
            timelineStep(
                icon: "bell.fill",
                title: "Day 2",
                description: "We'll remind you before your trial ends",
                isFirst: false,
                isLast: false
            )
            timelineStep(
                icon: "star.fill",
                title: "Day 3",
                description: "Trial ends. Cancel anytime — no charge",
                isFirst: false,
                isLast: true
            )
        }
    }

    private func timelineStep(icon: String, title: String, description: String, isFirst: Bool, isLast: Bool) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(spacing: 0) {
                if !isFirst {
                    Rectangle()
                        .fill(accent.opacity(0.3))
                        .frame(width: 2, height: 12)
                }

                ZStack {
                    Circle()
                        .fill(accent.opacity(0.15))
                        .frame(width: 30, height: 30)

                    Image(systemName: icon)
                        .font(.system(size: 13))
                        .foregroundColor(accent)
                }

                if !isLast {
                    Rectangle()
                        .fill(accent.opacity(0.3))
                        .frame(width: 2, height: 14)
                }
            }

            VStack(alignment: .leading, spacing: 2) {
                if !isFirst {
                    Spacer().frame(height: 12)
                }
                Text(title)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(primaryText)

                Text(description)
                    .font(.system(size: 13))
                    .foregroundColor(secondaryText)
                    .lineSpacing(1)
            }

            Spacer()
        }
    }

    // MARK: - Plan Cards

    private var planCardsSection: some View {
        HStack(spacing: 12) {
            planCard(
                title: "Weekly",
                price: weeklyProduct?.displayPrice ?? "...",
                period: "/week",
                subtitle: nil,
                planId: "com.kovneier.glptracker.weekly"
            )

            planCard(
                title: "Yearly",
                price: yearlyProduct?.displayPrice ?? "...",
                period: "/year",
                subtitle: "3-day free trial",
                planId: "com.kovneier.glptracker.yearly"
            )
        }
        .frame(height: 90)
    }

    private func planCard(title: String, price: String, period: String, subtitle: String?, planId: String) -> some View {
        let isSelected = selectedPlanId == planId

        return Button {
            withAnimation(.easeInOut(duration: 0.2)) {
                selectedPlanId = planId
            }
        } label: {
            VStack(spacing: 5) {
                Text(title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(primaryText)

                HStack(spacing: 0) {
                    Text(price)
                        .font(.system(size: 12, weight: .regular))
                    Text(period)
                        .font(.system(size: 10, weight: .light))
                }
                .foregroundColor(secondaryText)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(.system(size: 10))
                        .foregroundColor(secondaryText)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(maxHeight: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(isSelected ? accent.opacity(0.08) : cardBg)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(isSelected ? accent : Color(.systemGray5), lineWidth: isSelected ? 2 : 1)
            )
        }
    }

    // MARK: - Trial Info

    private var trialInfoText: some View {
        Group {
            if selectedPlanId == "com.kovneier.glptracker.yearly" {
                let price = yearlyProduct?.displayPrice ?? "..."
                Text("3-day free trial, then \(price)/year")
            } else {
                let price = weeklyProduct?.displayPrice ?? "..."
                Text("\(price)/week, cancel anytime")
            }
        }
        .font(.system(size: 14))
        .foregroundColor(secondaryText)
        .multilineTextAlignment(.center)
    }

    // MARK: - Money-Back Badge

    private var moneyBackBadge: some View {
        HStack(spacing: 8) {
            Image(systemName: "shield.fill")
                .font(.system(size: 16))
                .foregroundColor(accent)
            Text("14-Day Money-Back Guarantee")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(accent)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(accent.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Sticky Bottom Bar

    private var stickyBottomBar: some View {
        VStack(spacing: 6) {
            Button {
                purchase()
            } label: {
                Group {
                    if isPurchasing {
                        ProgressView().tint(.white)
                    } else {
                        Text(selectedPlanId == "com.kovneier.glptracker.yearly" ? "Start Free Trial" : "Subscribe")
                            .font(.system(size: 20, weight: .bold))
                    }
                }
                .foregroundColor(.white)
                .frame(maxWidth: isIPad ? 440 : .infinity)
                .frame(height: 56)
                .background(
                    LinearGradient(colors: [accent, accentLight], startPoint: .leading, endPoint: .trailing)
                )
                .cornerRadius(28)
            }
            .disabled(isPurchasing || subscriptionService.isLoading)
            .padding(.horizontal, 32)

            if selectedPlanId == "com.kovneier.glptracker.yearly" {
                Text("No payment now")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(accent)
                    .transition(.opacity)
            }

            Button {
                restorePurchases()
            } label: {
                Text("Restore Purchases")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(secondaryText)
            }
        }
        .padding(.top, 10)
        .padding(.bottom, 8)
        .animation(.easeInOut(duration: 0.2), value: selectedPlanId)
    }

    // MARK: - Features

    private var featuresSection: some View {
        VStack(spacing: 24) {
            Text("Stay Consistent. See Results.")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(primaryText)

            VStack(spacing: 20) {
                featureRow(icon: "syringe.fill", title: "Injection Tracker", description: "Log every shot with site rotation", highlighted: true)
                featureRow(icon: "chart.line.uptrend.xyaxis", title: "Weight Progress", description: "Visualize your transformation")
                featureRow(icon: "bell.badge.fill", title: "Smart Reminders", description: "Never miss injection day")
                featureRow(icon: "heart.fill", title: "Side Effect Diary", description: "Track symptoms over time")
                featureRow(icon: "doc.text.fill", title: "PDF Reports", description: "Export data for your doctor")
                featureRow(icon: "drop.fill", title: "Water & Protein", description: "Daily nutrition tracking")
            }
            .padding(.horizontal, 24)
        }
    }

    private func featureRow(icon: String, title: String, description: String, highlighted: Bool = false) -> some View {
        HStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(highlighted ? accent.opacity(0.15) : Color(.systemGray6))
                    .frame(width: 36, height: 36)

                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(accent)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(primaryText)

                Text(description)
                    .font(.system(size: 14))
                    .foregroundColor(secondaryText)
                    .lineLimit(2)
            }

            Spacer()
        }
    }

    // MARK: - Reviews

    private var reviewsSection: some View {
        VStack(spacing: 16) {
            Text("What Users Say")
                .font(.system(size: 24, weight: .bold))
                .foregroundColor(primaryText)
                .padding(.horizontal, 24)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    reviewCard(text: "I've been on Ozempic for 3 months and this app keeps me organized. The injection site rotation alone is worth it!", author: "Jessica M.")
                    reviewCard(text: "Finally an app that gets GLP-1 users. Tracking weight alongside my dose is a game changer for doctor visits.", author: "Robert K.")
                    reviewCard(text: "The side effect diary showed me nausea peaks on day 2 after my shot. So useful for planning meals around it.", author: "Amanda L.")
                    reviewCard(text: "PDF export is brilliant — I print it and hand it to my endocrinologist. Saves so much time at appointments.", author: "Dr. Patel (patient)")
                    reviewCard(text: "Lost 18 lbs in 2 months on Wegovy. This app helped me stay consistent and actually see my progress visually.", author: "Sarah T.")
                    reviewCard(text: "Reminder notifications are a lifesaver. I never miss my weekly shot anymore and the dose log is super easy.", author: "Mike D.")
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 4)
            }
        }
    }

    private func reviewCard(text: String, author: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 2) {
                ForEach(0..<5, id: \.self) { _ in
                    Image(systemName: "star.fill")
                        .font(.system(size: 11))
                        .foregroundColor(.yellow)
                }
            }
            Text("\"\(text)\"")
                .font(.system(size: 13))
                .foregroundColor(primaryText)
                .lineSpacing(2)
                .fixedSize(horizontal: false, vertical: true)
            Text("— \(author)")
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(secondaryText)
        }
        .padding(16)
        .frame(width: 220)
        .background(cardBg)
        .cornerRadius(14)
        .shadow(color: .black.opacity(0.06), radius: 6, x: 0, y: 2)
    }

    // MARK: - Features Carousel

    private var featuresCarouselSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 16) {
                featureCarouselCard(emoji: "💉", title: "Injection Log", subtitle: "Every dose tracked")
                featureCarouselCard(emoji: "🏋️", title: "Weight Chart", subtitle: "See your progress")
                featureCarouselCard(emoji: "📊", title: "Trends", subtitle: "Dose vs. weight")
                featureCarouselCard(emoji: "🔔", title: "Reminders", subtitle: "Never miss a day")
                featureCarouselCard(emoji: "📄", title: "PDF Export", subtitle: "Doctor-ready reports")
                featureCarouselCard(emoji: "💧", title: "Nutrition", subtitle: "Water & protein goals")
            }
            .padding(.horizontal, 24)
        }
    }

    private func featureCarouselCard(emoji: String, title: String, subtitle: String) -> some View {
        VStack(spacing: 8) {
            Text(emoji)
                .font(.system(size: 40))

            Text(title)
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(primaryText)
                .multilineTextAlignment(.center)

            Text(subtitle)
                .font(.system(size: 13))
                .foregroundColor(secondaryText)
                .multilineTextAlignment(.center)
        }
        .padding(20)
        .frame(width: 200)
        .background(accent.opacity(0.08))
        .cornerRadius(16)
    }

    // MARK: - Terms

    private var termsSection: some View {
        VStack(spacing: 8) {
            Text("Payment will be charged to your Apple ID account at the confirmation of purchase. Subscription automatically renews unless it is cancelled at least 24 hours before the end of the current period. Your account will be charged for renewal within 24 hours prior to the end of the current period.")
                .font(.system(size: 11))
                .foregroundColor(secondaryText.opacity(0.6))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            HStack(spacing: 16) {
                Link("Terms of Use", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                Link("Privacy Policy", destination: URL(string: "https://britetodo.com/privacypolicy.php")!)
            }
            .font(.system(size: 12))
            .foregroundColor(secondaryText)
        }
    }

    // MARK: - Actions

    private func purchase() {
        let product: Product?
        if selectedPlanId == "com.kovneier.glptracker.yearly" {
            product = yearlyProduct
        } else {
            product = weeklyProduct
        }

        guard let product = product else {
            errorMessage = "Product not available. Please try again."
            showError = true
            return
        }

        isPurchasing = true

        Task {
            do {
                try await subscriptionService.purchase(product)
                isPurchasing = false
                onComplete()
            } catch PurchaseError.userCancelled {
                isPurchasing = false
            } catch {
                isPurchasing = false
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }

    private func restorePurchases() {
        Task {
            do {
                try await subscriptionService.restore()
                restoreSuccess = subscriptionService.isPro
                showRestoreAlert = true
            } catch {
                restoreSuccess = false
                showRestoreAlert = true
            }
        }
    }
}

#Preview {
    PaywallView(source: "preview", onComplete: {})
        .environmentObject(SubscriptionService())
}
