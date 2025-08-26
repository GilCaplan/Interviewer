/**
 * Decodes HTML entities from a string by leveraging the browser's DOM parser.
 * @param {string | any} text The string containing HTML entities.
 * @returns {string} The decoded string.
 */
export const decodeHTMLEntities = (text) => {
    if (typeof text !== 'string' || !text) return '';
    const textArea = document.createElement('textarea');
    textArea.innerHTML = text;
    return textArea.value;
};