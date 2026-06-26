import SwiftUI
import CoreLocation

// Reads Core Location fixes and surfaces the iOS 15+ provenance flags
// (CLLocationSourceInformation: isSimulatedBySoftware / isProducedByAccessory).
final class LocationReader: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()

    @Published var status = "starting…"
    @Published var lat = 0.0
    @Published var lon = 0.0
    @Published var hAcc = 0.0
    @Published var updates = 0
    @Published var lastFix = "—"
    @Published var sourceInfoPresent = false
    @Published var simulatedBySoftware: Bool? = nil
    @Published var producedByAccessory: Bool? = nil

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest   // request precise
        manager.requestWhenInUseAuthorization()
    }

    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        switch m.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            status = "authorized — updating (ensure Precise = ON)"
            m.startUpdatingLocation()
        case .denied, .restricted:
            status = "DENIED — enable Location + Precise in Settings"
        case .notDetermined:
            status = "requesting permission…"
        @unknown default:
            status = "unknown auth state"
        }
    }

    func locationManager(_ m: CLLocationManager, didUpdateLocations locs: [CLLocation]) {
        guard let loc = locs.last else { return }
        updates += 1
        lat = loc.coordinate.latitude
        lon = loc.coordinate.longitude
        hAcc = loc.horizontalAccuracy
        lastFix = loc.timestamp.formatted(date: .omitted, time: .standard)
        if let src = loc.sourceInformation {          // iOS 15+
            sourceInfoPresent = true
            simulatedBySoftware = src.isSimulatedBySoftware
            producedByAccessory = src.isProducedByAccessory
        } else {
            sourceInfoPresent = false
            simulatedBySoftware = nil
            producedByAccessory = nil
        }
    }

    func locationManager(_ m: CLLocationManager, didFailWithError error: Error) {
        status = "error: \(error.localizedDescription)"
    }
}

struct ContentView: View {
    @StateObject private var reader = LocationReader()

    private func flag(_ b: Bool?) -> String {
        switch b {
        case .some(true):  return "TRUE"
        case .some(false): return "false"
        case .none:        return "—"
        }
    }

    private func row(_ k: String, _ v: String, emphasize: Bool = false) -> some View {
        HStack {
            Text(k)
            Spacer()
            Text(v).bold().foregroundStyle(emphasize ? .red : .primary)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("sourceInformation probe").font(.title2).bold()
            Text(reader.status).font(.footnote).foregroundStyle(.secondary)

            Divider()
            row("updates received", "\(reader.updates)")
            row("lat", String(format: "%.6f", reader.lat))
            row("lon", String(format: "%.6f", reader.lon))
            row("h-accuracy (m)", String(format: "%.1f", reader.hAcc))
            row("last fix", reader.lastFix)

            Divider()
            Text("CLLocationSourceInformation").font(.headline)
            row("present?", reader.sourceInfoPresent ? "yes" : "no (nil)")
            // The headline measurement — TRUE here would falsify paper §9.1.
            row("isSimulatedBySoftware", flag(reader.simulatedBySoftware),
                emphasize: reader.simulatedBySoftware == true)
            row("isProducedByAccessory", flag(reader.producedByAccessory),
                emphasize: reader.producedByAccessory == true)

            Spacer()
        }
        .padding()
        .monospaced()
    }
}
