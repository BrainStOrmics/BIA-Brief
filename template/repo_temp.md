<div class='cover-wrapper'>
<h2 style="font-size: 15pt;">{{Cover_Contract_ID}}</h2>
<div style='text-align: center;'>

<h2>{{Cover_Report_Title}}</h2>

<h2>{{Cover_Report_Date}}</h2>

<img src="{{Cover_Image_Path}}" alt="cover" />

<p style='font-size: 10pt; color: gray;'>{{Cover_Copyright_Text}}</p>

</div>

</div>

<style>
.report-table {
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    border: none;
    border-bottom: 1px solid #7c97c8;
    margin: 0 0 12px 0;
}

.report-table th,
.report-table td {
    border: 1px solid #7c97c8;
    padding: 4px 12px;
    vertical-align: middle;
    word-break: break-word;
}

.report-table th {
    background: #1f5a9e;
    color: #fff;
    font-weight: normal;
    text-align: center;
}

.report-table td {
    background: #fff;
    text-align: left;
}

.report-table p {
    margin: 0;
    text-indent: 0;
    line-height: 1.2;
}

.report-table th p,
.report-table td p {
    margin: 0;
    text-indent: 0;
    line-height: 1.2;
}

.faq-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px 0;
    font-family: Arial, "SimSun", "Songti SC", serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0d63b8;
    line-height: 1;
}

.faq-title .faq-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #0d63b8;
    flex: 0 0 18px;
}

.faq-title .faq-text {
    letter-spacing: 0.5px;
}

.ref-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px 0;
    font-family: Arial, "SimSun", "Songti SC", serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0d63b8;
    line-height: 1;
}

.ref-title .ref-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #0d63b8;
    flex: 0 0 18px;
}

.ref-title .ref-text {
    letter-spacing: 0.5px;
}

.help-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px 0;
    font-family: Arial, "SimSun", "Songti SC", serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0d63b8;
    line-height: 1;
}

.help-title .help-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #0d63b8;
    flex: 0 0 18px;
}

.help-title .help-text {
    letter-spacing: 0.5px;
}

.analysis-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px 0;
    font-family: Arial, "SimSun", "Songti SC", serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0d63b8;
    line-height: 1;
}

.analysis-title .analysis-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #0d63b8;
    flex: 0 0 18px;
}

.analysis-title .analysis-text {
    letter-spacing: 0.5px;
}

.method-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px 0;
    font-family: Arial, "SimSun", "Songti SC", serif;
    font-size: 16pt;
    font-weight: 700;
    color: #0d63b8;
    line-height: 1;
}

.method-title .method-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #0d63b8;
    flex: 0 0 18px;
}

.method-title .method-text {
    letter-spacing: 0.5px;
}
</style>

<style>
body, p, li, td, th, span, pre, div, h1, h2, h3, h4, h5, h6 {
    font-family: Arial, "SimSun", "Songti SC", serif;
}

body {
    font-size: 9pt;
}

table.report-table th,
table.report-table td,
.textbox-block,
.textbox-block pre {
    font-size: 9pt;
}

.toc-block {
    margin: 0 0 12px 0;
}

.toc-title {
    margin: 0 0 8px 0;
    font-size: 14pt;
    font-weight: 700;
    color: #0d63b8;
}

.toc-line {
    display: flex;
    align-items: baseline;
    gap: 0;
    margin: 0;
    line-height: 1.45;
}

.toc-item {
    flex: 0 1 auto;
    min-width: 0;
    white-space: normal;
}

.toc-level-0 .toc-item {
    padding-left: 0;
}

.toc-level-1 .toc-item {
    padding-left: 18px;
}

.toc-level-2 .toc-item {
    padding-left: 36px;
}

.toc-dots {
    flex: 1 1 auto;
    min-width: 10px;
    margin: 0 8px 3px 8px;
    border-bottom: 1px dashed #bdbdbd;
    opacity: 0.95;
}

.toc-page {
    flex: 0 0 auto;
    min-width: 1.5em;
    text-align: right;
}
</style>


<!-- __BODY_START__ -->
{{Toc_Block}}
<div style='page-break-after: always;'></div>

{{Body_Content}}

<div class='ref-title'><span class='ref-dot' aria-hidden='true'></span><span class='ref-text'>参考文献</span></div>

{{References_Block}}