const fs = require('fs');
const html = fs.readFileSync('test_rendered.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);

if (scriptMatch) {
    const jsCode = scriptMatch[1];
    fs.writeFileSync('test_script.js', jsCode);
    try {
        // use Function constructor to parse the syntax without executing
        new Function(jsCode);
        console.log("No syntax errors found in JavaScript!");
    } catch (e) {
        console.error("Syntax Error found:", e);
    }
} else {
    console.log("No script tag found.");
}
