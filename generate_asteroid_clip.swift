import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let width = 960
let height = 540
let fps = 24
let duration: Double = 2.8
let totalFrames = Int(duration * Double(fps))

let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let inputImageURL = cwd.appendingPathComponent("metior.jpg")
let outputURL = cwd.appendingPathComponent("asteroid_target_view.gif")

func loadCGImage(_ url: URL) -> CGImage? {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
    return CGImageSourceCreateImageAtIndex(src, 0, nil)
}

guard let asteroid = loadCGImage(inputImageURL) else {
    fputs("Could not load metior.jpg\n", stderr)
    exit(1)
}

if FileManager.default.fileExists(atPath: outputURL.path) {
    try? FileManager.default.removeItem(at: outputURL)
}

guard let destination = CGImageDestinationCreateWithURL(outputURL as CFURL, UTType.gif.identifier as CFString, totalFrames, nil) else {
    fputs("Could not create GIF destination\n", stderr)
    exit(1)
}

let gifProps: [CFString: Any] = [
    kCGImagePropertyGIFDictionary: [
        kCGImagePropertyGIFLoopCount: 0
    ]
]
CGImageDestinationSetProperties(destination, gifProps as CFDictionary)

let colorSpace = CGColorSpaceCreateDeviceRGB()

func drawCrosshair(_ ctx: CGContext, _ cx: CGFloat, _ cy: CGFloat) {
    ctx.setLineWidth(2)
    ctx.setStrokeColor(CGColor(red: 0.65, green: 0.9, blue: 1.0, alpha: 0.85))
    ctx.addEllipse(in: CGRect(x: cx - 14, y: cy - 14, width: 28, height: 28))
    ctx.strokePath()
    ctx.move(to: CGPoint(x: cx - 24, y: cy))
    ctx.addLine(to: CGPoint(x: cx - 7, y: cy))
    ctx.move(to: CGPoint(x: cx + 7, y: cy))
    ctx.addLine(to: CGPoint(x: cx + 24, y: cy))
    ctx.move(to: CGPoint(x: cx, y: cy - 24))
    ctx.addLine(to: CGPoint(x: cx, y: cy - 7))
    ctx.move(to: CGPoint(x: cx, y: cy + 7))
    ctx.addLine(to: CGPoint(x: cx, y: cy + 24))
    ctx.strokePath()
}

for frame in 0..<totalFrames {
    autoreleasepool {
        let bytesPerRow = width * 4
        guard let ctx = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: bytesPerRow,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue
        ) else { return }

        let t = Double(frame) / Double(max(1, totalFrames - 1))
        let cx = CGFloat(width) * 0.5
        let cy = CGFloat(height) * 0.56

        // dark space background
        ctx.setFillColor(CGColor(red: 0.01, green: 0.015, blue: 0.05, alpha: 1.0))
        ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))

        // stars
        srand48(frame * 13)
        for _ in 0..<180 {
            let x = drand48() * Double(width)
            let y = drand48() * Double(height)
            let r = CGFloat(0.3 + drand48() * 1.4)
            let alpha = CGFloat(0.35 + drand48() * 0.65)
            ctx.setFillColor(CGColor(red: 0.8, green: 0.92, blue: 1.0, alpha: alpha))
            ctx.fillEllipse(in: CGRect(x: x, y: y, width: Double(r), height: Double(r)))
        }

        // screen shake
        let shake = CGFloat(2.0 + t * 8.0)
        let sx = sin(CGFloat(t) * 34.0) * shake
        let sy = cos(CGFloat(t) * 28.0) * shake

        // inbound path (target POV)
        let startX = CGFloat(width) * 0.88
        let startY = CGFloat(height) * 0.08
        let astX = startX + (cx - startX) * CGFloat(pow(t, 1.3)) + sx
        let astY = startY + (cy - startY) * CGFloat(pow(t, 1.3)) + sy

        let scale = CGFloat(0.10 + pow(t, 2.2) * 1.8)
        let astW = CGFloat(asteroid.width) * scale
        let astH = CGFloat(asteroid.height) * scale

        // motion streak
        for i in 1...8 {
            let k = CGFloat(i) / 8.0
            let tx = astX + (startX - astX) * k * 0.35
            let ty = astY + (startY - astY) * k * 0.35
            let tw = astW * (1.0 - k * 0.6)
            let th = astH * (1.0 - k * 0.6)
            ctx.saveGState()
            ctx.setAlpha(0.12 * Double(1.0 - k))
            ctx.draw(asteroid, in: CGRect(x: tx - tw * 0.5, y: ty - th * 0.5, width: tw, height: th))
            ctx.restoreGState()
        }

        // glow
        let glowR = max(astW, astH) * 0.5
        ctx.setFillColor(CGColor(red: 1.0, green: 0.45, blue: 0.12, alpha: 0.28))
        ctx.fillEllipse(in: CGRect(x: astX - glowR, y: astY - glowR, width: glowR * 2, height: glowR * 2))

        // main asteroid rotated toward center
        ctx.saveGState()
        let angle = atan2(cy - astY, cx - astX)
        ctx.translateBy(x: astX, y: astY)
        ctx.rotate(by: angle)
        ctx.draw(asteroid, in: CGRect(x: -astW * 0.5, y: -astH * 0.5, width: astW, height: astH))
        ctx.restoreGState()

        drawCrosshair(ctx, cx + sx * 0.2, cy + sy * 0.2)

        if t > 0.9 {
            let a = (t - 0.9) / 0.1
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: min(1.0, a * 0.85)))
            ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }

        guard let frameImage = ctx.makeImage() else { return }
        let frameProps: [CFString: Any] = [
            kCGImagePropertyGIFDictionary: [
                kCGImagePropertyGIFDelayTime: 1.0 / Double(fps)
            ]
        ]
        CGImageDestinationAddImage(destination, frameImage, frameProps as CFDictionary)
    }
}

if CGImageDestinationFinalize(destination) {
    print("Created: \(outputURL.path)")
} else {
    fputs("Failed to write GIF\n", stderr)
    exit(1)
}
