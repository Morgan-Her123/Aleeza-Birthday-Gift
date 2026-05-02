import Foundation
import AVFoundation
import CoreGraphics

let width = 1280
let height = 720
let fps: Int32 = 30
let duration: Double = 3.0
let totalFrames = Int(duration * Double(fps))

let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let outputURL = cwd.appendingPathComponent("procedural_asteroid_target_view.mov")

if FileManager.default.fileExists(atPath: outputURL.path) {
    try? FileManager.default.removeItem(at: outputURL)
}

let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mov)
let settings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType(rawValue: "apcn"),
    AVVideoWidthKey: width,
    AVVideoHeightKey: height
]

let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
input.expectsMediaDataInRealTime = false

let attrs: [String: Any] = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
    kCVPixelBufferCGImageCompatibilityKey as String: true,
    kCVPixelBufferCGBitmapContextCompatibilityKey as String: true
]

let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: attrs)

if writer.canAdd(input) { writer.add(input) } else {
    fputs("Cannot add writer input\n", stderr)
    exit(1)
}

let started = writer.startWriting()
if !started {
    fputs("startWriting failed: \(String(describing: writer.error))\n", stderr)
    exit(1)
}
writer.startSession(atSourceTime: .zero)

let colorSpace = CGColorSpaceCreateDeviceRGB()

func drawStars(_ ctx: CGContext, frame: Int) {
    srand48(frame * 17)
    for _ in 0..<250 {
        let x = drand48() * Double(width)
        let y = drand48() * Double(height)
        let r = CGFloat(0.4 + drand48() * 1.8)
        let a = CGFloat(0.35 + drand48() * 0.65)
        ctx.setFillColor(CGColor(red: 0.78, green: 0.9, blue: 1.0, alpha: a))
        ctx.fillEllipse(in: CGRect(x: x, y: y, width: Double(r), height: Double(r)))
    }
}

func drawCrosshair(_ ctx: CGContext, x: CGFloat, y: CGFloat) {
    ctx.setStrokeColor(CGColor(red: 0.62, green: 0.88, blue: 1.0, alpha: 0.9))
    ctx.setLineWidth(2)
    ctx.addEllipse(in: CGRect(x: x - 14, y: y - 14, width: 28, height: 28))
    ctx.strokePath()
    ctx.move(to: CGPoint(x: x - 26, y: y))
    ctx.addLine(to: CGPoint(x: x - 7, y: y))
    ctx.move(to: CGPoint(x: x + 7, y: y))
    ctx.addLine(to: CGPoint(x: x + 26, y: y))
    ctx.move(to: CGPoint(x: x, y: y - 26))
    ctx.addLine(to: CGPoint(x: x, y: y - 7))
    ctx.move(to: CGPoint(x: x, y: y + 7))
    ctx.addLine(to: CGPoint(x: x, y: y + 26))
    ctx.strokePath()
}

func drawProceduralAsteroid(_ ctx: CGContext, center: CGPoint, radius: CGFloat, angle: CGFloat) {
    // Flame trail (behind asteroid)
    let tailLen = radius * 2.8
    let tx = center.x - cos(angle) * tailLen
    let ty = center.y - sin(angle) * tailLen
    let gradColors: [CGFloat] = [
        1.0, 0.95, 0.7, 0.8,
        1.0, 0.55, 0.15, 0.4,
        1.0, 0.3, 0.1, 0.0
    ]
    let grad = CGGradient(colorSpace: CGColorSpaceCreateDeviceRGB(), colorComponents: gradColors, locations: [0.0, 0.45, 1.0], count: 3)!
    ctx.saveGState()
    ctx.setBlendMode(.screen)
    ctx.drawRadialGradient(grad, startCenter: center, startRadius: radius * 0.1, endCenter: CGPoint(x: tx, y: ty), endRadius: tailLen, options: [])
    ctx.restoreGState()

    // Rocky body
    let pointsCount = 11
    var pts: [CGPoint] = []
    for i in 0..<pointsCount {
        let a = CGFloat(i) / CGFloat(pointsCount) * CGFloat.pi * 2
        let jitter = CGFloat(0.72 + drand48() * 0.35)
        let rr = radius * jitter
        pts.append(CGPoint(x: center.x + cos(a) * rr, y: center.y + sin(a) * rr))
    }
    ctx.beginPath()
    ctx.move(to: pts[0])
    for p in pts.dropFirst() { ctx.addLine(to: p) }
    ctx.closePath()
    ctx.setFillColor(CGColor(red: 0.28, green: 0.22, blue: 0.18, alpha: 1.0))
    ctx.fillPath()

    // Lava glow on front side
    let hx = center.x + cos(angle) * radius * 0.25
    let hy = center.y + sin(angle) * radius * 0.25
    ctx.setFillColor(CGColor(red: 1.0, green: 0.62, blue: 0.15, alpha: 0.85))
    ctx.fillEllipse(in: CGRect(x: hx - radius * 0.35, y: hy - radius * 0.35, width: radius * 0.7, height: radius * 0.7))
}

for frame in 0..<totalFrames {
    autoreleasepool {
        while !input.isReadyForMoreMediaData { usleep(500) }

        var px: CVPixelBuffer?
        let status = CVPixelBufferCreate(nil, width, height, kCVPixelFormatType_32ARGB, attrs as CFDictionary, &px)
        guard status == kCVReturnSuccess, let pixelBuffer = px else { return }

        CVPixelBufferLockBaseAddress(pixelBuffer, [])
        guard let base = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
            return
        }

        guard let ctx = CGContext(
            data: base,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: CVPixelBufferGetBytesPerRow(pixelBuffer),
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue
        ) else {
            CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
            return
        }

        let t = Double(frame) / Double(max(1, totalFrames - 1))
        let cx = CGFloat(width) * 0.5
        let cy = CGFloat(height) * 0.57

        ctx.setFillColor(CGColor(red: 0.01, green: 0.02, blue: 0.06, alpha: 1.0))
        ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
        drawStars(ctx, frame: frame)

        let shake = CGFloat(2.0 + t * 8.5)
        let sx = sin(CGFloat(t) * 33.0) * shake
        let sy = cos(CGFloat(t) * 29.0) * shake

        let startX = CGFloat(width) * 0.86
        let startY = CGFloat(height) * 0.11
        let ax = startX + (cx - startX) * CGFloat(pow(t, 1.35)) + sx
        let ay = startY + (cy - startY) * CGFloat(pow(t, 1.35)) + sy

        let radius = CGFloat(16 + pow(t, 2.35) * 220)
        let angle = atan2(cy - ay, cx - ax)

        // light bloom
        ctx.setFillColor(CGColor(red: 1.0, green: 0.45, blue: 0.12, alpha: 0.26))
        ctx.fillEllipse(in: CGRect(x: ax - radius * 0.95, y: ay - radius * 0.95, width: radius * 1.9, height: radius * 1.9))

        drawProceduralAsteroid(ctx, center: CGPoint(x: ax, y: ay), radius: radius, angle: angle)
        drawCrosshair(ctx, x: cx + sx * 0.18, y: cy + sy * 0.18)

        if t > 0.91 {
            let a = (t - 0.91) / 0.09
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: min(1.0, a * 0.9)))
            ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }

        let pts = CMTime(value: CMTimeValue(frame), timescale: fps)
        adaptor.append(pixelBuffer, withPresentationTime: pts)
        CVPixelBufferUnlockBaseAddress(pixelBuffer, [])
    }
}

input.markAsFinished()
writer.finishWriting {
    if writer.status == .completed {
        print("Created: \(outputURL.path)")
    } else {
        fputs("Video generation failed: \(String(describing: writer.error))\n", stderr)
        exit(1)
    }
}

RunLoop.main.run(until: Date().addingTimeInterval(1.0))
