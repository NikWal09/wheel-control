import QtQuick

// Przewijany wykres momentu (-1..+1) rysowany na Canvas.
Canvas {
    id: root
    property int maxSamples: 360
    property var samples: []
    property color lineColor: Theme.accent

    function push(v) {
        samples.push(v)
        if (samples.length > maxSamples)
            samples.shift()
        requestPaint()
    }
    function clear() {
        samples = []
        requestPaint()
    }

    renderStrategy: Canvas.Cooperative

    onPaint: {
        const ctx = getContext("2d")
        const w = width, h = height, mid = h / 2
        ctx.reset()

        // siatka
        ctx.strokeStyle = "#1F242C"
        ctx.lineWidth = 1
        for (let i = 1; i < 4; ++i) {
            const y = Math.round(h * i / 4) + 0.5
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
        }
        for (let i = 1; i < 8; ++i) {
            const x = Math.round(w * i / 8) + 0.5
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke()
        }
        ctx.strokeStyle = "#353C47"
        ctx.beginPath(); ctx.moveTo(0, mid + 0.5); ctx.lineTo(w, mid + 0.5); ctx.stroke()

        const n = samples.length
        if (n < 2)
            return
        const step = w / (maxSamples - 1)
        const x0 = w - (n - 1) * step
        const yOf = v => mid - Math.max(-1, Math.min(1, v)) * (mid - 4)

        // wypełnienie
        const grad = ctx.createLinearGradient(0, 0, 0, h)
        const c = root.lineColor
        grad.addColorStop(0, Qt.rgba(c.r, c.g, c.b, 0.35))
        grad.addColorStop(0.5, Qt.rgba(c.r, c.g, c.b, 0.02))
        grad.addColorStop(1, Qt.rgba(c.r, c.g, c.b, 0.35))
        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.moveTo(x0, mid)
        for (let i = 0; i < n; ++i)
            ctx.lineTo(x0 + i * step, yOf(samples[i]))
        ctx.lineTo(x0 + (n - 1) * step, mid)
        ctx.closePath()
        ctx.fill()

        // linia
        ctx.strokeStyle = root.lineColor
        ctx.lineWidth = 2
        ctx.lineJoin = "round"
        ctx.beginPath()
        for (let i = 0; i < n; ++i) {
            const x = x0 + i * step, y = yOf(samples[i])
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
    }
}
