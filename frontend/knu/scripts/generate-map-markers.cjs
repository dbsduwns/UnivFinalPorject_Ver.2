const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const MARKER_SCALE = 3;
const WIDTH = 96 * MARKER_SCALE;
const HEIGHT = 120 * MARKER_SCALE;
const SCALE = 4;

function color(hex) {
  const value = hex.replace("#", "");
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
    255,
  ];
}

function createCanvas() {
  return new Uint8Array(WIDTH * SCALE * HEIGHT * SCALE * 4);
}

function paint(canvas, predicate, fill) {
  const scaledWidth = WIDTH * SCALE;
  const scaledHeight = HEIGHT * SCALE;
  for (let y = 0; y < scaledHeight; y += 1) {
    for (let x = 0; x < scaledWidth; x += 1) {
      const px = (x + 0.5) / (SCALE * MARKER_SCALE);
      const py = (y + 0.5) / (SCALE * MARKER_SCALE);
      if (!predicate(px, py)) continue;
      const offset = (y * scaledWidth + x) * 4;
      canvas.set(fill, offset);
    }
  }
}

function circle(canvas, cx, cy, radius, fill) {
  paint(canvas, (x, y) => (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2, fill);
}

function polygon(canvas, points, fill) {
  paint(canvas, (x, y) => {
    let inside = false;
    for (let i = 0, j = points.length - 1; i < points.length; j = i, i += 1) {
      const [xi, yi] = points[i];
      const [xj, yj] = points[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
        inside = !inside;
      }
    }
    return inside;
  }, fill);
}

function rectangle(canvas, left, top, right, bottom, fill) {
  paint(canvas, (x, y) => x >= left && x <= right && y >= top && y <= bottom, fill);
}

function line(canvas, x1, y1, x2, y2, thickness, fill) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const lengthSquared = dx ** 2 + dy ** 2;
  paint(canvas, (x, y) => {
    const position = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / lengthSquared));
    const closestX = x1 + position * dx;
    const closestY = y1 + position * dy;
    return (x - closestX) ** 2 + (y - closestY) ** 2 <= (thickness / 2) ** 2;
  }, fill);
}

function drawPinBase(canvas, outer, inner) {
  polygon(canvas, [[48, 118], [7, 49], [89, 49]], outer);
  circle(canvas, 48, 45, 44, outer);
  polygon(canvas, [[48, 112], [12, 50], [84, 50]], inner);
  circle(canvas, 48, 45, 39, inner);
  circle(canvas, 48, 45, 22, color("#FFFFFF"));
}

function renderMarker(kind) {
  const canvas = createCanvas();
  const teal = color("#13708D");
  const amber = color("#F59E0B");
  const white = color("#FFFFFF");

  if (kind === "campus") {
    drawPinBase(canvas, teal, color("#D7EEEE"));
    polygon(canvas, [[31, 42], [48, 31], [65, 42]], teal);
    rectangle(canvas, 31, 43, 65, 47, teal);
    rectangle(canvas, 34, 50, 40, 61, teal);
    rectangle(canvas, 45, 50, 51, 61, teal);
    rectangle(canvas, 56, 50, 62, 61, teal);
    rectangle(canvas, 30, 63, 66, 67, teal);
  } else if (kind === "destination") {
    drawPinBase(canvas, white, amber);
    line(canvas, 35, 45, 44, 54, 6, amber);
    line(canvas, 44, 54, 62, 35, 6, amber);
  } else {
    drawPinBase(canvas, white, teal);
    polygon(canvas, [[32, 44], [48, 30], [64, 44]], teal);
    rectangle(canvas, 34, 42, 62, 62, teal);
    rectangle(canvas, 44, 51, 52, 62, white);
  }

  return downsample(canvas);
}

function downsample(source) {
  const output = Buffer.alloc(WIDTH * HEIGHT * 4);
  const sourceWidth = WIDTH * SCALE;
  for (let y = 0; y < HEIGHT; y += 1) {
    for (let x = 0; x < WIDTH; x += 1) {
      const sums = [0, 0, 0, 0];
      for (let sy = 0; sy < SCALE; sy += 1) {
        for (let sx = 0; sx < SCALE; sx += 1) {
          const sourceOffset = (((y * SCALE + sy) * sourceWidth) + x * SCALE + sx) * 4;
          for (let channel = 0; channel < 4; channel += 1) {
            sums[channel] += source[sourceOffset + channel];
          }
        }
      }
      const outputOffset = (y * WIDTH + x) * 4;
      for (let channel = 0; channel < 4; channel += 1) {
        output[outputOffset + channel] = Math.round(sums[channel] / (SCALE ** 2));
      }
    }
  }
  return output;
}

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const size = Buffer.alloc(4);
  size.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])));
  return Buffer.concat([size, typeBuffer, data, checksum]);
}

function encodePng(rgba) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(WIDTH, 0);
  header.writeUInt32BE(HEIGHT, 4);
  header[8] = 8;
  header[9] = 6;

  const scanlines = Buffer.alloc((WIDTH * 4 + 1) * HEIGHT);
  for (let y = 0; y < HEIGHT; y += 1) {
    const rowOffset = y * (WIDTH * 4 + 1);
    scanlines[rowOffset] = 0;
    rgba.copy(scanlines, rowOffset + 1, y * WIDTH * 4, (y + 1) * WIDTH * 4);
  }

  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", zlib.deflateSync(scanlines)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const outputDirectory = path.join(__dirname, "..", "src", "assets", "images");
for (const kind of ["origin", "destination", "campus"]) {
  fs.writeFileSync(
    path.join(outputDirectory, `map-marker-${kind}.png`),
    encodePng(renderMarker(kind)),
  );
}
