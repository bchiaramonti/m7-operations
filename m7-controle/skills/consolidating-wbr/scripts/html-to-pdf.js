#!/usr/bin/env node
/**
 * M7 WBR HTML to PDF Converter
 *
 * Converts a WBR Narrativo HTML file to PDF using Puppeteer.
 * Preserves M7-2026 design system styling, SVG charts, and print layout.
 *
 * Usage:
 *   node html-to-pdf.js <input.html> <output.pdf>
 *
 * Requirements:
 *   npm install puppeteer
 */

const puppeteer = require('puppeteer');
const path = require('path');

async function htmlToPdf(inputHtml, outputPdf) {
  const absolutePath = path.resolve(inputHtml);

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();

    // Set viewport for consistent rendering
    await page.setViewport({ width: 900, height: 1200, deviceScaleFactor: 2 });

    // Load the HTML file
    await page.goto(`file://${absolutePath}`, {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });

    // Wait for fonts to load
    await page.evaluateHandle('document.fonts.ready');

    // Small delay for final paint
    await new Promise(resolve => setTimeout(resolve, 500));

    // Generate PDF
    await page.pdf({
      path: outputPdf,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '20mm',
        bottom: '20mm',
        left: '15mm',
        right: '15mm',
      },
      preferCSSPageSize: true,
    });

    console.log(`PDF gerado: ${outputPdf}`);
  } finally {
    await browser.close();
  }
}

// CLI
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('Uso: node html-to-pdf.js <input.html> <output.pdf>');
  process.exit(1);
}

htmlToPdf(args[0], args[1]).catch(err => {
  console.error('Erro ao gerar PDF:', err.message);
  process.exit(1);
});
