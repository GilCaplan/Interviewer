import React, { useEffect, useState } from 'react';
import './TemplatesGallery.css';
import { Link, useNavigate } from 'react-router-dom';
import { getApiUrl, makeAuthenticatedRequest } from '../utils/authUtils';
import { useAuth } from '../context/AuthContext';
// import {fetchApi} from "../utils/api";

// Dynamic imports for PDF libraries to handle Docker environment issues
let jsPDF = null;
let html2canvas = null;

// Try to load PDF libraries with error handling
try {
  const jsPDFModule = require('jspdf');
  jsPDF = jsPDFModule.jsPDF || jsPDFModule.default || jsPDFModule;
} catch (error) {
  console.warn('jsPDF not available:', error.message);
}

try {
  html2canvas = require('html2canvas').default || require('html2canvas');
} catch (error) {
  console.warn('html2canvas not available:', error.message);
}

function TemplatesGallery() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [availableDifficulties, setAvailableDifficulties] = useState([]);
  const [availableSubjects, setAvailableSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCleanupModal, setShowCleanupModal] = useState(false);
  const [cleanupPreview, setCleanupPreview] = useState(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [currentExportTemplate, setCurrentExportTemplate] = useState(null);

  // PDF Export Function - Alternative approach without popups
  const exportToPDF = async (template, includeAnswers = true, event = null) => {
    if (event) {
      event.preventDefault(); // Prevent navigation
      event.stopPropagation();
    }
    
    try {
      console.log('Starting PDF export for template:', template.template_id);
      
      // Check authentication first
      if (!isAuthenticated) {
        alert('Please log in to export templates to PDF.');
        return;
      }
      
      // Show loading state (only if event is provided)
      let button, originalText;
      if (event) {
        button = event.target;
        originalText = button.textContent;
        button.textContent = '⏳ Loading...';
        button.disabled = true;
      }
      
      let templateData;
      
      // Check if the template from gallery already has questions
      console.log('Template from gallery:', {
        name: template.template_name,
        questionsCount: template.questions?.length || 0,
        hasQuestions: !!(template.questions && template.questions.length > 0)
      });
      
      // If template already has questions, use it directly
      if (template.questions && template.questions.length > 0) {
        console.log('Using template data from gallery - has questions already');
        templateData = template;
      } else {
        // Try to fetch full template details with questions
        console.log('Template has no questions, fetching from API...');
        try {
          console.log('Fetching template details from:', `${getApiUrl()}/api/templates/${template.template_id}`);
          const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates/${template.template_id}`, {
            method: 'GET'
          });
          
          if (response.ok) {
            const data = await response.json();
            templateData = data.template || data;
            console.log('Template data fetched successfully:', templateData);
            console.log('Questions found:', templateData.questions?.length || 0);
          } else {
            console.warn('Failed to fetch detailed template data, status:', response.status);
            const errorText = await response.text();
            console.warn('Error response:', errorText);
            templateData = template;
          }
        } catch (fetchError) {
          console.warn('Error fetching template details:', fetchError);
          
          // If authentication failed, show specific error
          if (fetchError.message.includes('Authentication') || fetchError.message.includes('token')) {
            // Reset button state
            if (button) {
              button.textContent = originalText;
              button.disabled = false;
            }
            alert('Authentication failed. Please log out and log back in, then try again.');
            return;
          }
          
          templateData = template;
        }
      }
      
      // Debug: log final template data
      console.log('Final template data for PDF:', {
        name: templateData.template_name,
        questionsCount: templateData.questions?.length || 0,
        hasQuestions: !!(templateData.questions && templateData.questions.length > 0)
      });
      
      // Create and download HTML file that can be printed as PDF
      await createAndDownloadPDF(templateData, includeAnswers);
      
      // Reset button state
      if (button) {
        button.textContent = originalText;
        button.disabled = false;
      }
      
      // Show success message with question count
      const questionCount = templateData.questions?.length || 0;
      const answerStatus = includeAnswers ? 'with answers' : 'practice version (no answers)';
      const message = questionCount > 0 
        ? `PDF export initiated with ${questionCount} questions (${answerStatus})! Check your downloads or use the print dialog to save as PDF.`
        : 'PDF export initiated! Note: This template appears to have no questions yet. Check your downloads or use the print dialog to save as PDF.';
      alert(message);
      
    } catch (error) {
      console.error('Error exporting to PDF:', error);
      
      // Reset button state
      if (event && event.target) {
        const button = event.target;
        button.textContent = '📄 Export';
        button.disabled = false;
      }
      
      alert('Failed to export template to PDF. Please try again or contact support if the problem persists.');
    }
  };

  // Show export options modal
  const showExportOptions = (template, event) => {
    event.preventDefault();
    event.stopPropagation();
    
    // Check authentication first
    if (!isAuthenticated) {
      alert('Please log in to export templates to PDF.');
      return;
    }
    
    setCurrentExportTemplate(template);
    setShowExportModal(true);
  };

  // Handle export option selection
  const handleExportOption = async (includeAnswers) => {
    setShowExportModal(false);
    if (currentExportTemplate) {
      await exportToPDF(currentExportTemplate, includeAnswers);
    }
    setCurrentExportTemplate(null);
  };

  // Debug function to inspect template data
  const debugTemplateData = async (template, event) => {
    event.preventDefault();
    event.stopPropagation();
    
    console.log('=== TEMPLATE DEBUG ===');
    console.log('Original template from gallery:', template);
    console.log('Template ID:', template.template_id);
    console.log('Template keys:', Object.keys(template));
    
    // Test all possible API endpoints
    const endpoints = [
      `${getApiUrl()}/api/templates/${template.template_id}`,
      `${getApiUrl().replace('/api', '')}/templates/${template.template_id}`,
      `${getApiUrl()}/api/templates/${template.template_id}/questions`,
      `${getApiUrl()}/api/templates/${template.template_id}/backup1`,
      `${getApiUrl()}/templates/${template.template_id}/backup2`
    ];
    
    for (const endpoint of endpoints) {
      try {
        console.log(`\n--- Testing endpoint: ${endpoint} ---`);
        const response = await fetch(endpoint);
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Response data:', data);
          console.log('Questions in response:', data.questions?.length || data.template?.questions?.length || 0);
        } else {
          const errorText = await response.text();
          console.log('Error response:', errorText);
        }
      } catch (error) {
        console.log('Fetch error:', error);
      }
    }
    
    alert('Debug complete! Check the browser console (F12) for detailed information about all API endpoints.');
  };

  // Create and download PDF file with fallback
  const createAndDownloadPDF = async (template, includeAnswers = true) => {
    try {
      // Try the advanced PDF generation first
      if (jsPDF && html2canvas) {
        // Create PDF content element
        const pdfElement = createPDFElement(template, includeAnswers);
        document.body.appendChild(pdfElement);
        
        // Convert HTML to canvas
        const canvas = await html2canvas(pdfElement, {
          scale: 2,
          useCORS: true,
          allowTaint: true,
          backgroundColor: '#ffffff'
        });
        
        // Remove the temporary element
        document.body.removeChild(pdfElement);
        
        // Create PDF from canvas
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF();
        const imgWidth = 210; // A4 width in mm
        const pageHeight = 295; // A4 height in mm
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        let heightLeft = imgHeight;
        let position = 0;
        
        // Add first page
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
        
        // Add additional pages if needed
        while (heightLeft >= 0) {
          position = heightLeft - imgHeight;
          pdf.addPage();
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
          heightLeft -= pageHeight;
        }
        
        // Download the PDF
        const suffix = includeAnswers ? '-with-answers' : '-practice';
        const filename = `${template.template_name || 'interview-template'}${suffix}.pdf`;
        pdf.save(filename);
        
        return; // Success, exit function
      }
    } catch (error) {
      console.warn('Advanced PDF generation failed, falling back to print-optimized HTML:', error);
    }
    
    // Fallback: Create print-optimized HTML that can be easily converted to PDF
    console.log('Using print-optimized HTML fallback (PDF libraries not available)');
    try {
      const htmlContent = generatePrintOptimizedHTML(template, includeAnswers);
      
      // Try to open in new window for printing
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        
        // Auto-trigger print dialog after content loads
        printWindow.onload = () => {
          setTimeout(() => {
            printWindow.focus();
            printWindow.print();
          }, 500);
        };
      } else {
        // Popup blocked, download HTML file
        const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const suffix = includeAnswers ? '-with-answers' : '-practice';
        link.download = `${template.template_name || 'interview-template'}${suffix}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        // Update success message for HTML download
        alert('PDF libraries not available in this environment. An HTML file has been downloaded instead. You can open it in your browser and use "Print > Save as PDF" to create your PDF file.');
      }
    } catch (error) {
      console.error('Error in PDF generation fallback:', error);
      throw error;
    }
  };

  // Create DOM element for PDF generation
  const createPDFElement = (template, includeAnswers = true) => {
    const questions = template.questions || [];
    const templateName = template.template_name || 'Interview Template';
    const description = template.description || 'Professional interview template';
    
    // Create main container
    const container = document.createElement('div');
    container.style.cssText = `
      font-family: Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: #333;
      width: 800px;
      margin: 0 auto;
      padding: 20px;
      background: white;
    `;
    
    // Header
    const header = document.createElement('div');
    header.style.cssText = `
      text-align: center;
      border-bottom: 3px solid #4a90e2;
      padding-bottom: 20px;
      margin-bottom: 30px;
    `;
    
    const title = document.createElement('h1');
    title.textContent = templateName;
    title.style.cssText = `
      color: #4a90e2;
      margin: 0 0 10px 0;
      font-size: 28px;
      font-weight: bold;
    `;
    header.appendChild(title);
    
    const desc = document.createElement('p');
    desc.textContent = description;
    desc.style.cssText = `margin: 10px 0; font-size: 16px;`;
    header.appendChild(desc);
    
    if (!includeAnswers) {
      const practiceIndicator = document.createElement('p');
      practiceIndicator.textContent = '📝 PRACTICE VERSION - Answers not included';
      practiceIndicator.style.cssText = `
        color: #e91e63;
        font-weight: bold;
        font-size: 16px;
        margin: 15px 0;
      `;
      header.appendChild(practiceIndicator);
    }
    
    container.appendChild(header);
    
    // Metadata
    const metadata = document.createElement('div');
    metadata.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 30px;
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
    `;
    
    const metadataLeft = document.createElement('div');
    const metadataRight = document.createElement('div');
    
    const metadataItems = [
      [`Subject: ${template.subject || 'N/A'}`, `Created by: ${template.created_by || 'Anonymous'}`],
      [`Difficulty: ${template.difficulty || 'N/A'}`, `Created: ${template.metadata?.created_at ? new Date(template.metadata.created_at).toLocaleDateString() : 'Unknown'}`],
      [`Questions: ${questions.length}`, `Version: ${template.metadata?.version || 1}`]
    ];
    
    metadataItems.forEach(([left, right]) => {
      const leftItem = document.createElement('div');
      leftItem.textContent = left;
      leftItem.style.cssText = `margin-bottom: 8px; font-size: 14px;`;
      metadataLeft.appendChild(leftItem);
      
      const rightItem = document.createElement('div');
      rightItem.textContent = right;
      rightItem.style.cssText = `margin-bottom: 8px; font-size: 14px;`;
      metadataRight.appendChild(rightItem);
    });
    
    metadata.appendChild(metadataLeft);
    metadata.appendChild(metadataRight);
    container.appendChild(metadata);
    
    // Questions
    if (questions.length === 0) {
      const noQuestions = document.createElement('div');
      noQuestions.style.cssText = `
        text-align: center;
        padding: 40px;
        color: #6c757d;
        border: 2px dashed #dee2e6;
        border-radius: 8px;
        background: #f8f9fa;
      `;
      noQuestions.innerHTML = `
        <h3 style="color: #495057; margin-bottom: 15px;">⚠️ No questions available</h3>
        <p>This template doesn't contain any questions yet.</p>
      `;
      container.appendChild(noQuestions);
    } else {
      questions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.style.cssText = `
          margin-bottom: 30px;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 20px;
          background: white;
        `;
        
        // Question header
        const questionHeader = document.createElement('div');
        questionHeader.textContent = `Question ${index + 1} - ${(question.type || 'QUESTION').replace('_', ' ').toUpperCase()}`;
        questionHeader.style.cssText = `
          background: #4a90e2;
          color: white;
          padding: 10px 15px;
          margin: -20px -20px 20px -20px;
          border-radius: 8px 8px 0 0;
          font-weight: bold;
        `;
        questionDiv.appendChild(questionHeader);
        
        // Question text
        const questionText = document.createElement('div');
        questionText.innerHTML = `<strong>Question:</strong><br>${question.question_text || 'No question text provided'}`;
        questionText.style.cssText = `margin-bottom: 15px; line-height: 1.5;`;
        questionDiv.appendChild(questionText);
        
        // Multiple choice options
        if (question.type === 'multiple_choice' && question.options) {
          const optionsDiv = document.createElement('div');
          optionsDiv.innerHTML = '<strong>Options:</strong>';
          optionsDiv.style.cssText = `margin-bottom: 15px;`;
          
          const optionsList = document.createElement('div');
          optionsList.style.cssText = `margin-left: 20px; margin-top: 8px;`;
          
          question.options.forEach((option, idx) => {
            const optionItem = document.createElement('div');
            optionItem.textContent = `${String.fromCharCode(65 + idx)}. ${option}`;
            optionItem.style.cssText = `margin-bottom: 5px;`;
            optionsList.appendChild(optionItem);
          });
          
          optionsDiv.appendChild(optionsList);
          questionDiv.appendChild(optionsDiv);
        }
        
        if (includeAnswers) {
          // Correct answer
          if (question.correct_answer) {
            const answerDiv = document.createElement('div');
            answerDiv.innerHTML = `<strong style="color: #28a745;">Correct Answer:</strong><br>${question.correct_answer}`;
            answerDiv.style.cssText = `margin-bottom: 15px; line-height: 1.5;`;
            questionDiv.appendChild(answerDiv);
          }
          
          // Explanation
          if (question.explanation) {
            const explanationDiv = document.createElement('div');
            explanationDiv.innerHTML = `<strong>Explanation:</strong><br>${question.explanation}`;
            explanationDiv.style.cssText = `
              background: #f8f9fa;
              padding: 15px;
              border-radius: 6px;
              border-left: 4px solid #4a90e2;
              margin-top: 15px;
              line-height: 1.5;
            `;
            questionDiv.appendChild(explanationDiv);
          }
          
          // Sample answer
          if (question.sample_answer) {
            const sampleDiv = document.createElement('div');
            sampleDiv.innerHTML = `<strong>Sample Answer:</strong><br>${question.sample_answer}`;
            sampleDiv.style.cssText = `margin-top: 15px; line-height: 1.5;`;
            questionDiv.appendChild(sampleDiv);
          }
        } else {
          // Answer space for practice version
          const answerSpace = document.createElement('div');
          answerSpace.style.cssText = `
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #17a2b8;
            border-radius: 6px;
          `;
          
          const answerLabel = document.createElement('div');
          answerLabel.textContent = 'Your answer:';
          answerLabel.style.cssText = `color: #666; font-style: italic; margin-bottom: 8px;`;
          answerSpace.appendChild(answerLabel);
          
          const answerBox = document.createElement('div');
          answerBox.style.cssText = `
            border: 1px solid #ddd;
            min-height: 60px;
            background: white;
            border-radius: 4px;
          `;
          answerSpace.appendChild(answerBox);
          
          questionDiv.appendChild(answerSpace);
        }
        
        container.appendChild(questionDiv);
      });
    }
    
    // Footer
    const footer = document.createElement('div');
    footer.textContent = `Generated on ${new Date().toLocaleString()} | Interview Process Assistant`;
    footer.style.cssText = `
      text-align: center;
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid #eee;
      color: #666;
      font-size: 12px;
    `;
    container.appendChild(footer);
    
    // Position off-screen
    container.style.position = 'absolute';
    container.style.left = '-9999px';
    container.style.top = '0';
    
    return container;
  };

  // Generate print-optimized HTML for fallback
  const generatePrintOptimizedHTML = (template, includeAnswers = true) => {
    const questions = template.questions || [];
    const templateName = template.template_name || 'Interview Template';
    const description = template.description || 'Professional interview template';
    
    // Helper function to safely escape HTML
    const escapeHtml = (text) => {
      if (!text) return '';
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };
    
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${escapeHtml(templateName)}</title>
        <meta charset="UTF-8">
        <style>
          @page {
            margin: 0.75in;
            size: A4;
          }
          
          body {
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: white;
          }
          
          .header {
            text-align: center;
            border-bottom: 3px solid #4a90e2;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          
          .header h1 {
            color: #4a90e2;
            margin: 0 0 10px 0;
            font-size: 28px;
            font-weight: bold;
          }
          
          .practice-indicator {
            color: #e91e63;
            font-weight: bold;
            font-size: 16px;
            margin: 15px 0;
          }
          
          .metadata {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            page-break-inside: avoid;
          }
          
          .metadata div {
            font-size: 14px;
            margin-bottom: 8px;
          }
          
          .metadata strong {
            color: #495057;
          }
          
          .question {
            margin-bottom: 30px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            background: white;
            page-break-inside: avoid;
          }
          
          .question-header {
            background: #4a90e2;
            color: white;
            padding: 10px 15px;
            margin: -20px -20px 20px -20px;
            border-radius: 8px 8px 0 0;
            font-weight: bold;
          }
          
          .question-content {
            margin-bottom: 15px;
          }
          
          .options {
            margin-left: 20px;
            margin-top: 8px;
          }
          
          .option {
            margin-bottom: 5px;
          }
          
          .correct-answer {
            color: #28a745;
            font-weight: bold;
          }
          
          .explanation {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #4a90e2;
            margin-top: 15px;
          }
          
          .answer-space {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #17a2b8;
            border-radius: 6px;
          }
          
          .answer-box {
            border: 1px solid #ddd;
            min-height: 60px;
            background: white;
            border-radius: 4px;
            margin-top: 8px;
          }
          
          .no-questions {
            text-align: center;
            padding: 40px;
            color: #6c757d;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            background: #f8f9fa;
          }
          
          .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 12px;
          }
          
          .instructions {
            background: #e3f2fd;
            border: 1px solid #bbdefb;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
          }
          
          .instructions h4 {
            color: #1976d2;
            margin: 0 0 10px 0;
          }
          
          @media print {
            .instructions {
              display: none;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${escapeHtml(templateName)}</h1>
          <p>${escapeHtml(description)}</p>
          ${!includeAnswers ? '<p class="practice-indicator">📝 PRACTICE VERSION - Answers not included</p>' : ''}
        </div>
        
        <div class="metadata">
          <div>
            <div><strong>Subject:</strong> ${escapeHtml(template.subject || 'N/A')}</div>
            <div><strong>Difficulty:</strong> ${escapeHtml(template.difficulty || 'N/A')}</div>
            <div><strong>Questions:</strong> ${questions.length}</div>
          </div>
          <div>
            <div><strong>Created by:</strong> ${escapeHtml(template.created_by || 'Anonymous')}</div>
            <div><strong>Created:</strong> ${template.metadata?.created_at ? new Date(template.metadata.created_at).toLocaleDateString() : 'Unknown'}</div>
            <div><strong>Version:</strong> ${template.metadata?.version || 1}</div>
          </div>
        </div>
        
        <div class="instructions">
          <h4>📋 How to Save as PDF</h4>
          <p>This window will automatically open the print dialog. Select <strong>"Save as PDF"</strong> as the destination to create your PDF file.</p>
        </div>
        
        <div class="questions">
          ${questions.length === 0 ? `
            <div class="no-questions">
              <h3>⚠️ No questions available</h3>
              <p>This template doesn't contain any questions yet.</p>
            </div>
          ` : questions.map((question, index) => `
            <div class="question">
              <div class="question-header">
                Question ${index + 1} - ${escapeHtml(question.type?.replace('_', ' ').toUpperCase() || 'QUESTION')}
              </div>
              
              <div class="question-content">
                <strong>Question:</strong><br>
                ${escapeHtml(question.question_text || 'No question text provided')}
              </div>
              
              ${question.type === 'multiple_choice' && question.options && Array.isArray(question.options) ? `
                <div class="question-content">
                  <strong>Options:</strong>
                  <div class="options">
                    ${question.options.map((option, idx) => `
                      <div class="option">${String.fromCharCode(65 + idx)}. ${escapeHtml(option)}</div>
                    `).join('')}
                  </div>
                </div>
              ` : ''}
              
              ${includeAnswers && question.correct_answer ? `
                <div class="question-content">
                  <strong class="correct-answer">Correct Answer:</strong><br>
                  ${escapeHtml(question.correct_answer)}
                </div>
              ` : ''}
              
              ${includeAnswers && question.explanation ? `
                <div class="explanation">
                  <strong>Explanation:</strong><br>
                  ${escapeHtml(question.explanation)}
                </div>
              ` : ''}
              
              ${includeAnswers && question.sample_answer ? `
                <div class="question-content">
                  <strong>Sample Answer:</strong><br>
                  ${escapeHtml(question.sample_answer)}
                </div>
              ` : ''}
              
              ${!includeAnswers ? `
                <div class="answer-space">
                  <div style="color: #666; font-style: italic;">Your answer:</div>
                  <div class="answer-box"></div>
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
        
        <div class="footer">
          Generated on ${new Date().toLocaleString()} | Interview Process Assistant
        </div>
      </body>
      </html>
    `;
  };

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoading(true);
        setError('');
        
        console.log('Loading templates from:', `${getApiUrl()}/api/templates`);
        console.log('User authenticated:', isAuthenticated);
        console.log('User info:', user);
        
        // Check if user has auth token
        const token = localStorage.getItem('token') || 
                     (localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')).sessionToken : null);
        console.log('Auth token available:', !!token);
        
        if (!isAuthenticated) {
          setError('Please login to view templates.');
          setLoading(false);
          return;
        }
        
        const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates`, {
          method: 'GET'
        });

        console.log('Templates response status:', response.status);

        if (response.ok) {
          const data = await response.json();
          console.log('Templates data received:', data);
          const templates = data.templates || [];
          console.log('Number of templates:', templates.length);
          setTemplates(templates);

          // Dynamically extract difficulties and subjects (case-insensitive uniqueness)
          const difficulties = [
            ...new Set(templates.map(t => t.difficulty?.toLowerCase()).filter(Boolean)),
          ];
          const subjects = [
            ...new Set(templates.map(t => t.subject?.toLowerCase()).filter(Boolean)),
          ];
          setAvailableDifficulties(difficulties);
          setAvailableSubjects(subjects);
        } else {
          const errorData = await response.json();
          setError(errorData.error || 'Failed to load templates');
        }
      } catch (err) {
        console.error('Error loading templates:', err);
        if (err.message.includes('Authentication expired')) {
          setError('Please login again to view templates.');
        } else if (err.message.includes('No authentication token')) {
          setError('Please login to view templates.');
        } else {
          setError(`Error: ${err.message}`);
        }
      } finally {
        setLoading(false);
      }
    };

    loadTemplates();
  }, []);

  const loadCleanupPreview = async () => {
    setCleanupLoading(true);
    try {
      const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates/cleanup-preview?user_only=true`, {
        method: 'GET'
      });

      if (response.ok) {
        const data = await response.json();
        setCleanupPreview(data);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to load cleanup preview');
      }
    } catch (err) {
      console.error('Error loading cleanup preview:', err);
      setError('Failed to load cleanup preview');
    } finally {
      setCleanupLoading(false);
    }
  };

  const performCleanup = async (dryRun = true) => {
    setCleanupLoading(true);
    try {
      const response = await makeAuthenticatedRequest(`${getApiUrl()}/api/templates/cleanup-duplicates`, {
        method: 'POST',
        body: JSON.stringify({
          dry_run: dryRun,
          user_only: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        if (!dryRun) {
          // Refresh templates after actual cleanup
          window.location.reload();
        } else {
          setCleanupPreview(data);
        }
        
        return data;
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to cleanup templates');
      }
    } catch (err) {
      console.error('Error during cleanup:', err);
      setError(err.message);
      throw err;
    } finally {
      setCleanupLoading(false);
    }
  };

  const handleShowCleanup = () => {
    setShowCleanupModal(true);
    loadCleanupPreview();
  };


  // Group templates by template_key and show only latest version of each
/*  const groupedTemplates = templates.reduce((acc, template) => {
    const key = template.template_key || `legacy_${template.template_id}`;
    
    if (!acc[key] || template.metadata?.version > (acc[key].metadata?.version || 1)) {
      acc[key] = template;
    }
    
    return acc;
  }, {});

  const uniqueTemplates = Object.values(groupedTemplates);*/

  const filteredTemplates = templates.filter(template => {
    const nameMatch = template.template_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const difficultyMatch =
      !difficultyFilter || template.difficulty?.toLowerCase() === difficultyFilter;
    const subjectMatch =
      !subjectFilter || template.subject?.toLowerCase() === subjectFilter;
    return nameMatch && difficultyMatch && subjectMatch;
  });

  return (
    <div className="template-gallery">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>Templates Gallery</h2>
        <button 
          onClick={handleShowCleanup}
          style={{
            backgroundColor: '#ff9800',
            color: 'white',
            padding: '10px 16px',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer',
            fontWeight: '600'
          }}
        >
          🧹 Cleanup Duplicates
        </button>
      </div>
      
      {loading && <div className="loading">Loading templates...</div>}
      {error && (
        <div className="error-message">
          {error}
          {!isAuthenticated && (
            <div style={{ marginTop: '15px' }}>
              <button 
                onClick={() => navigate('/login')}
                style={{
                  backgroundColor: '#2196F3',
                  color: 'white',
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Go to Login
              </button>
            </div>
          )}
        </div>
      )}
      
      <div className="template-controls">
        <input
          type="text"
          placeholder="Search by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <select
          value={difficultyFilter}
          onChange={(e) => setDifficultyFilter(e.target.value)}
        >
          <option value="">All Difficulties</option>
          {availableDifficulties.map((diff, idx) => (
            <option key={idx} value={diff}>{diff.charAt(0).toUpperCase() + diff.slice(1)}</option>
          ))}
        </select>

        <select
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
        >
          <option value="">All Subjects</option>
          {availableSubjects.map((subject, idx) => (
            <option key={idx} value={subject}>{subject.charAt(0).toUpperCase() + subject.slice(1)}</option>
          ))}
        </select>
      </div>

      <div className="template-stats" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <p>Found {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''}</p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            backgroundColor: '#4CAF50',
            color: 'white',
            padding: '8px 16px',
            border: 'none',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: 'pointer'
          }}
        >
          🔄 Refresh
        </button>
      </div>

      <div className="template-grid">
        {filteredTemplates.length === 0 && !loading ? (
          <div className="no-templates">
            <p>No templates found.</p>
            <p>Create a new template using collaborative sessions!</p>
          </div>
        ) : (
          filteredTemplates.map((template, index) => (
            <div key={template.template_id} className="template-card-wrapper">
              <Link to={`/template/${template.template_id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="template-card">
                  <div className="template-card-content">
                    <h3>{template.template_name || 'Untitled Template'}</h3>
                    {template.metadata?.version > 1 && (
                      <p style={{ color: '#2196F3', fontSize: '0.85rem', fontWeight: '600', margin: '5px 0' }}>
                        📝 Version {template.metadata.version}
                      </p>
                    )}
                    <p><strong>Difficulty:</strong> {template.difficulty || 'N/A'}</p>
                    <p><strong>Subject:</strong> {template.subject || 'N/A'}</p>
                    {template.sub_subject && <p><strong>Sub-subject:</strong> {template.sub_subject}</p>}
                    <p><strong>Created:</strong> {template.metadata?.created_at ? new Date(template.metadata.created_at).toLocaleString() : 'Unknown'}</p>
                    {template.metadata?.updated_at && template.metadata.updated_at !== template.metadata.created_at && (
                      <p><strong>Updated:</strong> {new Date(template.metadata.updated_at).toLocaleString()}</p>
                    )}
                    <p><strong># Questions:</strong> {template.questions?.length || template.metadata?.question_count || 0}</p>
                    <p><strong>Author:</strong> {template.created_by || 'Anonymous'}</p>
                    {template.description && <p className="template-description">{template.description}</p>}
                    {template.is_public && <span className="public-badge">PUBLIC</span>}
                  </div>
                </div>
              </Link>
              
              <div className="template-card-actions">
                <button 
                  className="action-btn view-btn"
                  onClick={() => navigate(`/template/${template.template_id}`)}
                  title="View template details"
                >
                  👁️ View
                </button>
                <button 
                  className="action-btn pdf-btn"
                  onClick={(e) => showExportOptions(template, e)}
                  title="Download printable version for PDF export"
                >
                  📄 Export
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Cleanup Modal */}
      {showCleanupModal && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div className="modal-content" style={{
            background: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
            minWidth: '500px',
            maxWidth: '700px',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333', textAlign: 'center' }}>
              🧹 Template Cleanup
            </h3>
            
            {cleanupLoading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <p>🔍 Scanning for duplicate templates...</p>
              </div>
            ) : cleanupPreview ? (
              <div>
                <div style={{ 
                  backgroundColor: '#f0f8ff', 
                  padding: '15px', 
                  borderRadius: '8px', 
                  marginBottom: '20px',
                  border: '1px solid #2196F3'
                }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#1976d2' }}>📊 Cleanup Summary</h4>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Total Templates:</strong> {cleanupPreview.total_templates}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Unique Templates:</strong> {cleanupPreview.unique_templates}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px' }}>
                    <strong>Duplicate Groups:</strong> {cleanupPreview.duplicate_groups}
                  </p>
                  <p style={{ margin: '5px 0', fontSize: '14px', color: '#ff5722' }}>
                    <strong>Templates to Remove:</strong> {cleanupPreview.duplicates_found}
                  </p>
                </div>

                {cleanupPreview.duplicates_found > 0 ? (
                  <div>
                    <h4 style={{ color: '#333', marginBottom: '15px' }}>🗂️ Duplicate Groups Found:</h4>
                    <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '20px' }}>
                      {Object.entries(cleanupPreview.groups).map(([groupKey, templates]) => (
                        <div key={groupKey} style={{
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          padding: '12px',
                          marginBottom: '10px',
                          backgroundColor: '#fafafa'
                        }}>
                          <h5 style={{ margin: '0 0 8px 0', color: '#333' }}>
                            "{templates[0].template_name}"
                          </h5>
                          <p style={{ fontSize: '12px', color: '#666', margin: '0 0 8px 0' }}>
                            {templates.length} duplicates found
                          </p>
                          {templates.map((template, index) => (
                            <div key={template.template_id} style={{
                              fontSize: '12px',
                              padding: '4px 8px',
                              backgroundColor: index === 0 ? '#e8f5e9' : '#ffebee',
                              border: `1px solid ${index === 0 ? '#4caf50' : '#f44336'}`,
                              borderRadius: '4px',
                              margin: '2px 0'
                            }}>
                              {index === 0 ? '✅ KEEP' : '🗑️ REMOVE'} - 
                              Version {template.metadata?.version || 1} - 
                              {template.metadata?.question_count || 0} questions - 
                              {new Date(template.metadata?.created_at).toLocaleDateString()}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>

                    <div style={{ 
                      backgroundColor: '#fff3cd', 
                      padding: '15px', 
                      borderRadius: '8px', 
                      marginBottom: '20px',
                      border: '1px solid #ffc107'
                    }}>
                      <p style={{ margin: 0, fontSize: '14px', color: '#856404' }}>
                        ⚠️ <strong>Warning:</strong> This will permanently delete {cleanupPreview.duplicates_found} duplicate templates. 
                        The newest version or highest version number will be kept for each group.
                      </p>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                      <button
                        onClick={() => setShowCleanupModal(false)}
                        style={{
                          padding: '12px 20px',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '16px',
                          cursor: 'pointer',
                          backgroundColor: '#6c757d',
                          color: 'white',
                          fontWeight: '600'
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={async () => {
                          if (window.confirm(`Are you sure you want to delete ${cleanupPreview.duplicates_found} duplicate templates? This cannot be undone.`)) {
                            try {
                              await performCleanup(false);
                              alert('Duplicate templates have been removed successfully!');
                              setShowCleanupModal(false);
                            } catch (error) {
                              alert('Failed to cleanup templates: ' + error.message);
                            }
                          }
                        }}
                        disabled={cleanupLoading}
                        style={{
                          padding: '12px 20px',
                          border: 'none',
                          borderRadius: '6px',
                          fontSize: '16px',
                          cursor: cleanupLoading ? 'not-allowed' : 'pointer',
                          backgroundColor: cleanupLoading ? '#ccc' : '#dc3545',
                          color: 'white',
                          fontWeight: '600'
                        }}
                      >
                        {cleanupLoading ? '🔄 Cleaning...' : `🗑️ Remove ${cleanupPreview.duplicates_found} Duplicates`}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px' }}>
                    <p style={{ fontSize: '18px', color: '#4caf50', marginBottom: '10px' }}>
                      ✅ No duplicate templates found!
                    </p>
                    <p style={{ color: '#666', fontSize: '14px' }}>
                      Your template library is clean and organized.
                    </p>
                    <button
                      onClick={() => setShowCleanupModal(false)}
                      style={{
                        padding: '12px 20px',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '16px',
                        cursor: 'pointer',
                        backgroundColor: '#4caf50',
                        color: 'white',
                        fontWeight: '600',
                        marginTop: '20px'
                      }}
                    >
                      Great!
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <p>Failed to load cleanup preview.</p>
                <button
                  onClick={() => setShowCleanupModal(false)}
                  style={{
                    padding: '12px 20px',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '16px',
                    cursor: 'pointer',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    fontWeight: '600'
                  }}
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Export Options Modal */}
      {showExportModal && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div className="modal-content" style={{
            background: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
            minWidth: '400px',
            maxWidth: '500px'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333', textAlign: 'center' }}>
              📄 Choose Export Option
            </h3>
            
            <div style={{ marginBottom: '25px' }}>
              <p style={{ color: '#666', textAlign: 'center', lineHeight: '1.5' }}>
                How would you like to export "<strong>{currentExportTemplate?.template_name}</strong>"?
              </p>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <button
                onClick={() => handleExportOption(true)}
                style={{
                  padding: '15px 20px',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  cursor: 'pointer',
                  backgroundColor: '#28a745',
                  color: 'white',
                  fontWeight: '600',
                  textAlign: 'left',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => e.target.style.backgroundColor = '#218838'}
                onMouseOut={(e) => e.target.style.backgroundColor = '#28a745'}
              >
                <div style={{ fontSize: '18px', marginBottom: '5px' }}>
                  ✅ <strong>Complete Version (with answers)</strong>
                </div>
                <div style={{ fontSize: '14px', opacity: '0.9' }}>
                  Includes correct answers, explanations, and grading criteria
                </div>
              </button>
              
              <button
                onClick={() => handleExportOption(false)}
                style={{
                  padding: '15px 20px',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '16px',
                  cursor: 'pointer',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  fontWeight: '600',
                  textAlign: 'left',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => e.target.style.backgroundColor = '#1976D2'}
                onMouseOut={(e) => e.target.style.backgroundColor = '#2196F3'}
              >
                <div style={{ fontSize: '18px', marginBottom: '5px' }}>
                  📝 <strong>Practice Version (no answers)</strong>
                </div>
                <div style={{ fontSize: '14px', opacity: '0.9' }}>
                  Questions only with space to write answers - perfect for practice!
                </div>
              </button>
            </div>
            
            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <button
                onClick={() => setShowExportModal(false)}
                style={{
                  padding: '10px 20px',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  backgroundColor: 'white',
                  color: '#666',
                  fontWeight: '500'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TemplatesGallery;