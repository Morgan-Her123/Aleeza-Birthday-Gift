import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let width = 960
let height = 540
let fps = 24
let duration: Double = 3.0
let totalFrames = Int(duration * Double(fps))

let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let outputURL = cwd.appendingPathComponent("procedural_asteroid_target_view.gif")

if FileManager.default.fileExists(atPath: outputURL.path) {
    try? FileManager.default.removeItem(at: outputURL)
}

guard let destination = CGImageDestinationCreateWithURL(outputURL as CFURL, UTType.gif.identifier as CFString, totalFrames, nil) else {
    fputs("Could not create GIF destination\n", stderr)
    exit(1)
}

let gifProps: [CFString: Any] = [
    kCGImagePropertyGIFDictionary: [kCGImagePropertyGIFLoopCount: 0]
]
CGImageDestinationSetProperties(destination, gifProps as CFDictionary)

let colorSpace = CGColorSpaceCreateDeviceRGB()

func drawStars(_ ctx: CGContext, frame: Int, width: Int, height: Int) {
    srand48(frame * 31)
    for _ in 0..<220 {
        let x = drand48() * Double(width)
        let y = drand48() * Double(height)
        let r = CGFloat(0.3 + drand48() * 1.6)
        let a = CGFloat(0.35 + drand48() * 0.65)
        ctx.setFillColor(CGColor(red: 0.82, green: 0.92, blue: 1.0, alpha: a))
        ctx.fillEllipse(in: CGRect(x: x, y: y, width: Double(r), height: Double(r)))
    }
}

func drawCrosshair(_ ctx: CGContext, x: CGFloat, y: CGFloat) {
    ctx.setStrokeColor(CGColor(red: 0.62, green: 0.88, blue: 1.0, alpha: 0.9))
    ctx.setLineWidth(2)
    ctx.addEllipse(in: CGRect(x: x - 14, y: y - 14, width: 28, height: 28))
    ctx.strokePath()
    ctx.move(to: CGPoint(x: x - 26, y: y)); ctx.addLine(to: CGPoint(x: x - 7, y: y))
    ctx.move(to: CGPoint(x: x + 7, y: y)); ctx.addLine(to: CGPoint(x: x + 26, y: y))
    ctx.move(to: CGPoint(x: x, y: y - 26)); ctx.addLine(to: CGPoint(x: x, y: y - 7))
    ctx.move(to: CGPoint(x: x, y: y + 7)); ctx.addLine(to: CGPoint(x: x, y: y + 26))
    ctx.strokePath()
}

func drawProceduralAsteroid(_ ctx: CGContext, center: CGPoint, radius: CGFloat, angle: CGFloat) {
    let tailLen = radius * 2.8
    let tx = center.x - cos(angle) * tailLen
    let ty = center.y - sin(angle) * tailLen

    let gradColors: [CGFloat] = [
        1.0, 0.95, 0.7, 0.80,
        1.0, 0.55, 0.15, 0.45,
        1.0, 0.3, 0.1, 0.00
    ]
    let grad = CGGradient(colorSpace: CGColorSpaceCreateDeviceRGB(), colorComponents: gradColors, locations: [0.0, 0.5, 1.0], count: 3)!

    ctx.saveGState()
    ctx.setBlendMode(.screen)
    ctx.drawRadialGradient(grad, startCenter: center, startRadius: radius * 0.1, endCenter: CGPoint(x: tx, y: ty), endRadius: tailLen, options: [])
    ctx.restoreGState()

    var pts: [CGPoint] = []
    let n = 12
    for i in 0..<n {
        let a = CGFloat(i) / CGFloat(n) * .pi * 2
        let rr = radius * CGFloat(0.72 + drand48() * 0.34)
        pts.append(CGPoint(x: center.x + cos(a) * rr, y: center.y + sin(a) * rr))
    }

    ctx.beginPath()
    ctx.move(to: pts[0])
    for p in pts.dropFirst() { ctx.addLine(to: p) }
    ctx.closePath()
    ctx.setFillColor(CGColor(red: 0.28, green: 0.22, blue: 0.17, alpha: 1.0))
    ctx.fillPath()

    let hx = center.x + cos(angle) * radius * 0.22
    let hy = center.y + sin(angle) * radius * 0.22
    ctx.setFillColor(CGColor(red: 1.0, green: 0.62, blue: 0.12, alpha: 0.9))
    ctx.fillEllipse(in: CGRect(x: hx - radius * 0.34, y: hy - radius * 0.34, width: radius * 0.68, height: radius * 0.68))
}

for frame in 0..<totalFrames {
    autoreleasepool {
        guard let ctx = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue
        ) else { return }

        let t = Double(frame) / Double(max(1, totalFrames - 1))
        let cx = CGFloat(width) * 0.5
        let cy = CGFloat(height) * 0.57

        ctx.setFillColor(CGColor(red: 0.01, green: 0.02, blue: 0.06, alpha: 1.0))
        ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
        drawStars(ctx, frame: frame, width: width, height: height)

        let shake = CGFloat(2.0 + t * 8.0)
        let sx = sin(CGFloat(t) * 34.0) * shake
        let sy = cos(CGFloat(t) * 28.0) * shake

        let startX = CGFloat(width) * 0.86
        let startY = CGFloat(height) * 0.10
        let ax = startX + (cx - startX) * CGFloat(pow(t, 1.35)) + sx
        let ay = startY + (cy - startY) * CGFloat(pow(t, 1.35)) + sy

        let radius = CGFloat(14 + pow(t, 2.3) * 190)
        let angle = atan2(cy - ay, cx - ax)

        ctx.setFillColor(CGColor(red: 1.0, green: 0.45, blue: 0.12, alpha: 0.28))
        ctx.fillEllipse(in: CGRect(x: ax - radius, y: ay - radius, width: radius * 2, height: radius * 2))

        drawProceduralAsteroid(ctx, center: CGPoint(x: ax, y: ay), radius: radius, angle: angle)
        drawCrosshair(ctx, x: cx + sx * 0.18, y: cy + sy * 0.18)

        if t > 0.91 {
            let a = (t - 0.91) / 0.09
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: min(1.0, a * 0.9)))
            ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }

        guard let img = ctx.makeImage() else { return }
        let frameProps: [CFString: Any] = [
            kCGImagePropertyGIFDictionary: [kCGImagePropertyGIFDelayTime: 1.0 / Double(fps)]
        ]
        CGImageDestinationAddImage(destination, img, frameProps as CFDictionary)
    }
}

if CGImageDestinationFinalize(destination) {
    print("Created: \(outputURL.path)")
} else {
    fputs("Failed to write GIF\n", stderr)
    exit(1)
}
