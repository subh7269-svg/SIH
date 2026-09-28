import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { InvestigationReport } from '../types';

export function generateForensicReportPdf(report: InvestigationReport): void {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = 210;
  const pageHeight = 297;
  const leftMargin = 14;
  const rightMargin = 14;
  const contentWidth = pageWidth - leftMargin - rightMargin; // 182 mm
  let currentY = 18;

  const checkPageBreak = (neededHeight: number) => {
    if (currentY + neededHeight > pageHeight - 20) {
      doc.addPage();
      currentY = 20;
    }
  };

  // ==========================================
  // 1. TOP HEADER BANNER (Dark Navy LeadForge Styling)
  // ==========================================
  doc.setFillColor(15, 23, 42); // slate-900 / navy
  doc.rect(leftMargin, currentY, contentWidth, 34, 'F');

  // Cyan & Emerald accent line at top of banner
  doc.setFillColor(16, 185, 129); // emerald
  doc.rect(leftMargin, currentY, contentWidth * 0.6, 1.5, 'F');
  doc.setFillColor(6, 182, 212); // cyan
  doc.rect(leftMargin + contentWidth * 0.6, currentY, contentWidth * 0.4, 1.5, 'F');

  // Subtitle / Brand
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(16, 185, 129); // emerald
  doc.text('LEADFORGE // FORENSIC INTELLIGENCE BRIEF', leftMargin + 5, currentY + 7);

  // Main Report Title
  doc.setFontSize(14);
  doc.setTextColor(248, 250, 252); // slate-50
  const titleText = doc.splitTextToSize(report.title.toUpperCase(), contentWidth - 65);
  doc.text(titleText, leftMargin + 5, currentY + 14);

  // Target Entity
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(148, 163, 184); // slate-400
  doc.text('TARGET ENTITY:', leftMargin + 5, currentY + 22);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(6, 182, 212); // cyan
  doc.text(`${report.entity_id} (${report.entity_type})`, leftMargin + 32, currentY + 22);

  // Right-side Meta in Banner
  const rightX = leftMargin + contentWidth - 5;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text(`REPORT ID: ${report.report_id}`, rightX, currentY + 7, { align: 'right' });
  doc.text(`DATE: ${new Date(report.generated_at).toUTCString()}`, rightX, currentY + 12, { align: 'right' });
  
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(245, 158, 11); // amber
  doc.text('LAW ENFORCEMENT SENSITIVE', rightX, currentY + 18, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(148, 163, 184);
  doc.text('STRICTLY CONFIDENTIAL', rightX, currentY + 23, { align: 'right' });

  currentY += 38;

  // ==========================================
  // 2. MANDATORY FORENSIC DISCLAIMER
  // ==========================================
  checkPageBreak(25);
  doc.setFillColor(254, 242, 242); // red-50
  doc.setDrawColor(239, 68, 68); // red-500
  doc.setLineWidth(0.4);
  
  const disclaimerBody = doc.splitTextToSize(report.disclaimer, contentWidth - 10);
  const disclaimerBoxHeight = 10 + (disclaimerBody.length * 3.8);
  doc.roundedRect(leftMargin, currentY, contentWidth, disclaimerBoxHeight, 1.5, 1.5, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(185, 28, 28); // red-700
  doc.text('MANDATORY FORENSIC DISCLAIMER & LEGAL NOTICE', leftMargin + 5, currentY + 5.5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(127, 29, 29); // red-900
  doc.text(disclaimerBody, leftMargin + 5, currentY + 9.5);

  currentY += disclaimerBoxHeight + 5;

  // ==========================================
  // 3. RISK ASSESSMENT SCORECARDS
  // ==========================================
  checkPageBreak(22);
  const cardWidth = (contentWidth - 6) / 3;
  const cardHeight = 18;

  // Card 1: Composite Priority Score
  doc.setFillColor(241, 245, 249);
  doc.setDrawColor(203, 213, 225);
  doc.roundedRect(leftMargin, currentY, cardWidth, cardHeight, 1.5, 1.5, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text('COMPOSITE PRIORITY SCORE', leftMargin + cardWidth / 2, currentY + 5, { align: 'center' });
  doc.setFontSize(14);
  doc.setTextColor(16, 185, 129); // emerald
  doc.text(`${report.risk_score} / 100`, leftMargin + cardWidth / 2, currentY + 13, { align: 'center' });

  // Card 2: Severity Category
  const card2X = leftMargin + cardWidth + 3;
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(card2X, currentY, cardWidth, cardHeight, 1.5, 1.5, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text('SEVERITY CATEGORY', card2X + cardWidth / 2, currentY + 5, { align: 'center' });
  doc.setFontSize(14);
  const sev = report.severity.toUpperCase();
  if (sev === 'CRITICAL') doc.setTextColor(220, 38, 38);
  else if (sev === 'HIGH') doc.setTextColor(234, 88, 12);
  else if (sev === 'MEDIUM') doc.setTextColor(217, 119, 6);
  else doc.setTextColor(37, 99, 235);
  doc.text(sev, card2X + cardWidth / 2, currentY + 13, { align: 'center' });

  // Card 3: Isolation Forest Outlier Score
  const card3X = leftMargin + (cardWidth * 2) + 6;
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(card3X, currentY, cardWidth, cardHeight, 1.5, 1.5, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text('ISOLATION FOREST OUTLIER SCORE', card3X + cardWidth / 2, currentY + 5, { align: 'center' });
  doc.setFontSize(14);
  doc.setTextColor(8, 145, 178); // cyan-600
  doc.text(report.anomaly_score.toFixed(3), card3X + cardWidth / 2, currentY + 13, { align: 'center' });

  currentY += cardHeight + 6;

  // ==========================================
  // 4. MATHEMATICAL EXPLAINABILITY & DEVIATION REASONS
  // ==========================================
  checkPageBreak(25);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42); // slate-900
  doc.text('1. Mathematical Explainability & Deviation Reasons', leftMargin, currentY);
  
  doc.setDrawColor(16, 185, 129);
  doc.setLineWidth(0.6);
  doc.line(leftMargin, currentY + 1.5, leftMargin + contentWidth, currentY + 1.5);
  currentY += 6;

  if (report.explanation && report.explanation.length > 0) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(51, 65, 85); // slate-700
    report.explanation.forEach(reason => {
      const wrapped = doc.splitTextToSize(`•  ${reason}`, contentWidth - 4);
      checkPageBreak(wrapped.length * 4.2 + 2);
      doc.text(wrapped, leftMargin + 2, currentY);
      currentY += wrapped.length * 4.2 + 1;
    });
  } else {
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    doc.text('No statistical deviations flagged by the ML pipeline for this entity.', leftMargin + 2, currentY);
    currentY += 6;
  }
  currentY += 4;

  // ==========================================
  // 4B. FEATURE BREAKDOWN TABLE (if available)
  // ==========================================
  if (report.feature_breakdown && Object.keys(report.feature_breakdown).length > 0) {
    checkPageBreak(20);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(30, 41, 59);
    doc.text('Feature Space Breakdown (Multivariate Vectors)', leftMargin, currentY);
    currentY += 3;

    const featureRows = Object.entries(report.feature_breakdown).map(([feat, val]) => [
      feat,
      typeof val === 'number' ? (Number.isInteger(val) ? val.toString() : val.toFixed(4)) : String(val),
    ]);

    autoTable(doc, {
      startY: currentY,
      head: [['Engine Feature Vector', 'Observed Entity Value']],
      body: featureRows,
      margin: { left: leftMargin, right: rightMargin },
      theme: 'grid',
      headStyles: {
        fillColor: [30, 41, 59],
        textColor: [241, 245, 249],
        fontSize: 8,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 7.5,
        textColor: [30, 41, 59],
        cellPadding: 1.8,
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252],
      },
      showHead: 'everyPage',
      pageBreak: 'auto',
    });

    currentY = (doc as any).lastAutoTable.finalY + 6;
  }

  // ==========================================
  // 5. ASSOCIATED BLOCKCHAIN TRANSACTION RECORDS
  // ==========================================
  checkPageBreak(25);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42);
  const txCount = report.transaction_evidence?.length || 0;
  doc.text(`2. Associated Blockchain Transaction Records (${txCount} Records)`, leftMargin, currentY);

  doc.setDrawColor(16, 185, 129);
  doc.setLineWidth(0.6);
  doc.line(leftMargin, currentY + 1.5, leftMargin + contentWidth, currentY + 1.5);
  currentY += 5;

  if (report.transaction_evidence && report.transaction_evidence.length > 0) {
    const txRows = report.transaction_evidence.map(tx => {
      const vol = tx.input_total !== undefined ? tx.input_total : (tx.output_total !== undefined ? tx.output_total : '-');
      const fee = tx.fee !== undefined ? tx.fee : '-';
      const volStr = typeof vol === 'number' ? `${vol.toFixed(4)} BTC` : String(vol);
      const feeStr = typeof fee === 'number' ? `${fee.toFixed(6)} BTC` : String(fee);
      return [
        tx.txid || 'N/A',
        volStr,
        feeStr,
        tx.timestamp || 'N/A',
        tx.script_type || 'Standard',
      ];
    });

    autoTable(doc, {
      startY: currentY,
      head: [['Transaction Identifier (TXID)', 'Volume', 'Fee', 'Observed Timestamp', 'Script Type']],
      body: txRows,
      margin: { left: leftMargin, right: rightMargin },
      theme: 'grid',
      headStyles: {
        fillColor: [15, 23, 42],
        textColor: [241, 245, 249],
        fontSize: 8,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 7.5,
        textColor: [15, 23, 42],
        cellPadding: 2,
        overflow: 'linebreak',
      },
      columnStyles: {
        0: { cellWidth: 70, font: 'courier' },
        1: { cellWidth: 26 },
        2: { cellWidth: 24 },
        3: { cellWidth: 38 },
        4: { cellWidth: 24 },
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252],
      },
      showHead: 'everyPage',
      pageBreak: 'auto',
    });

    currentY = (doc as any).lastAutoTable.finalY + 6;
  } else {
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    doc.text('No transaction records linked to this entity.', leftMargin + 2, currentY);
    currentY += 8;
  }

  // ==========================================
  // 6. NETWORK WIRE OBSERVATIONS (RELAY PROVENANCE)
  // ==========================================
  checkPageBreak(25);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42);
  const ipCount = report.network_observations?.length || 0;
  doc.text(`3. Network Wire Observations / Relay Provenance (${ipCount} Relays)`, leftMargin, currentY);

  doc.setDrawColor(16, 185, 129);
  doc.setLineWidth(0.6);
  doc.line(leftMargin, currentY + 1.5, leftMargin + contentWidth, currentY + 1.5);
  currentY += 4.5;

  doc.setFont('helvetica', 'italic');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text('Network relay records demonstrate P2P propagation endpoints and do not assert cryptographic ownership.', leftMargin, currentY);
  currentY += 4;

  if (report.network_observations && report.network_observations.length > 0) {
    const ipRows = report.network_observations.map(ipo => [
      ipo.ip || 'N/A',
      ipo.country || 'UNKNOWN',
      ipo.asn || 'UNKNOWN',
      ipo.timestamp || 'N/A',
    ]);

    autoTable(doc, {
      startY: currentY,
      head: [['Relay IP Address', 'Country Jurisdiction', 'Autonomous System (ASN)', 'Observation Timestamp']],
      body: ipRows,
      margin: { left: leftMargin, right: rightMargin },
      theme: 'grid',
      headStyles: {
        fillColor: [15, 23, 42],
        textColor: [241, 245, 249],
        fontSize: 8,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 7.5,
        textColor: [15, 23, 42],
        cellPadding: 2,
        overflow: 'linebreak',
      },
      columnStyles: {
        0: { cellWidth: 45, font: 'courier' },
        1: { cellWidth: 40 },
        2: { cellWidth: 45 },
        3: { cellWidth: 52 },
      },
      alternateRowStyles: {
        fillColor: [248, 250, 252],
      },
      showHead: 'everyPage',
      pageBreak: 'auto',
    });

    currentY = (doc as any).lastAutoTable.finalY + 6;
  } else {
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8.5);
    doc.setTextColor(100, 116, 139);
    doc.text('No network relay IP observations recorded for this entity.', leftMargin + 2, currentY);
    currentY += 8;
  }

  // ==========================================
  // 7. INVESTIGATOR NOTES & OBSERVATIONS
  // ==========================================
  if (report.analyst_notes && report.analyst_notes.trim()) {
    checkPageBreak(25);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);
    doc.text('4. Investigator Notes & Actionable Directions', leftMargin, currentY);

    doc.setDrawColor(16, 185, 129);
    doc.setLineWidth(0.6);
    doc.line(leftMargin, currentY + 1.5, leftMargin + contentWidth, currentY + 1.5);
    currentY += 5;

    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(203, 213, 225);
    const notesText = doc.splitTextToSize(report.analyst_notes, contentWidth - 8);
    const notesHeight = 6 + notesText.length * 4.2;
    checkPageBreak(notesHeight + 4);

    doc.roundedRect(leftMargin, currentY, contentWidth, notesHeight, 1.5, 1.5, 'FD');
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(30, 41, 59);
    doc.text(notesText, leftMargin + 4, currentY + 5);
    currentY += notesHeight + 6;
  }

  // ==========================================
  // 8. EVIDENCE INTEGRITY & SYSTEM PROVENANCE
  // ==========================================
  checkPageBreak(20);
  doc.setFillColor(241, 245, 249);
  doc.setDrawColor(203, 213, 225);
  doc.roundedRect(leftMargin, currentY, contentWidth, 14, 1.5, 1.5, 'FD');
  
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  doc.text('SYSTEM PROVENANCE & CHAIN OF CUSTODY', leftMargin + 4, currentY + 4.5);
  
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text(
    `Brief generated deterministically by LeadForge Forensic Intelligence Engine v1.0.0 (Offline Air-gapped Mode). Authenticated as official analytical work product.`,
    leftMargin + 4,
    currentY + 9
  );

  // ==========================================
  // 9. RECURRING RUNNING HEADER & FOOTER ON ALL PAGES
  // ==========================================
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);

    // Running Header (skip on page 1 where banner exists)
    if (i > 1) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7);
      doc.setTextColor(148, 163, 184);
      doc.text('LEADFORGE FORENSIC INTELLIGENCE BRIEF', leftMargin, 10);
      doc.setFont('helvetica', 'normal');
      doc.text(`REF: ${report.report_id}  |  TARGET: ${report.entity_id}`, leftMargin + 65, 10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(245, 158, 11);
      doc.text('LAW ENFORCEMENT SENSITIVE', pageWidth - rightMargin, 10, { align: 'right' });

      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.3);
      doc.line(leftMargin, 12, pageWidth - rightMargin, 12);
    }

    // Running Footer on every page
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.3);
    doc.line(leftMargin, pageHeight - 12, pageWidth - rightMargin, pageHeight - 12);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(148, 163, 184);
    doc.text('CONFIDENTIAL // INVESTIGATIVE LEAD BRIEF // NOT DEFINITIVE PROOF OF GUILT', leftMargin, pageHeight - 7.5);
    
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(71, 85, 105);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - rightMargin, pageHeight - 7.5, { align: 'right' });
  }

  // Trigger download
  doc.save(`${report.report_id}.pdf`);
}
