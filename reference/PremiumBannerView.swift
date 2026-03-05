import SwiftUI

// Full-screen premium lock overlay — clean frosted glass, tappable
struct PremiumLockedOverlay: View {
    let title: String
    let subtitle: String
    let onUpgrade: () -> Void

    var body: some View {
        Rectangle()
            .fill(.ultraThinMaterial)
            .ignoresSafeArea()
            .onTapGesture { onUpgrade() }
    }
}

// Inline banner — place inside scroll content to upsell
struct PremiumBannerView: View {
    let message: String
    let onUpgrade: () -> Void

    var body: some View {
        Button(action: onUpgrade) {
            HStack(spacing: 14) {
                Image(systemName: "star.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(.white)
                    .padding(10)
                    .background(AppTheme.accent.opacity(0.85))
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 2) {
                    Text("Upgrade to Premium")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(.primary)
                    Text(message)
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(AppTheme.accent)
            }
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(AppTheme.accent.opacity(0.07))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(AppTheme.accent.opacity(0.25), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }
}
