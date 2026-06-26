import SwiftUI

// Minimal SwiftUI app entry point.
// Purpose: read CLLocation.sourceInformation live while Phantom's DVT
// keep-alive injects a simulated fix, to directly measure whether
// `isSimulatedBySoftware` fires for the developer/DVT channel (paper §9.1).
@main
struct SourceInfoProbeApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
