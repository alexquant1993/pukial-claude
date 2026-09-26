import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
let fast = CommandLine.arguments.count > 2 && CommandLine.arguments[2] == "fast"
guard let image = NSImage(contentsOfFile: path), let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let start = Date()
let request = VNRecognizeTextRequest()
request.recognitionLevel = fast ? .fast : .accurate
request.recognitionLanguages = ["es-ES", "en-US"]
request.usesLanguageCorrection = !fast
try VNImageRequestHandler(cgImage: cg).perform([request])
let w = Double(cg.width), h = Double(cg.height)
var lines: [[String: Any]] = []
for obs in request.results ?? [] {
  guard let top = obs.topCandidates(1).first else { continue }
  let b = obs.boundingBox
  lines.append(["text": top.string, "confidence": top.confidence,
    "rect": [Int(b.minX * w), Int((1 - b.maxY) * h), Int(b.width * w), Int(b.height * h)]])
}
let out: [String: Any] = ["ms": Int(Date().timeIntervalSince(start) * 1000), "size": [Int(w), Int(h)], "lines": lines]
print(String(data: try JSONSerialization.data(withJSONObject: out, options: [.sortedKeys]), encoding: .utf8)!)
