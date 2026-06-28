// Global state
let candidateId = null;
let currentJobId = null;
let activeCallId = null;
let wsConn = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const resumeUpload = document.getElementById('resumeUpload');
const fileNameLabel = document.getElementById('fileName');
const candidateForm = document.getElementById('candidateForm');
const jobCard = document.getElementById('jobCard');
const jobForm = document.getElementById('jobForm');
const jdUrlInput = document.getElementById('jdUrl');
const scrapeBtn = document.getElementById('scrapeBtn');
const companyNameInput = document.getElementById('companyName');
const jobTitleInput = document.getElementById('jobTitle');
const jdTextInput = document.getElementById('jdText');
const hrPhoneInput = document.getElementById('hrPhone');
const terminalScreen = document.getElementById('terminalScreen');
const simulatorArea = document.getElementById('simulatorArea');
const simulatorInput = document.getElementById('simulatorInput');
const simulatorSendBtn = document.getElementById('simulatorSendBtn');
const callStatusBadge = document.getElementById('callStatusBadge');
const historyTableBody = document.getElementById('historyTableBody');
const transcriptModal = document.getElementById('transcriptModal');
const transcriptBox = document.getElementById('transcriptBox');
const modalCloseBtn = document.getElementById('modalCloseBtn');
const mockModeIndicator = document.getElementById('mockModeIndicator');

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadCallHistory();
    setupDropzone();
});

// Dropzone file binding
function setupDropzone() {
    dropzone.addEventListener('click', () => resumeUpload.click());
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-focus)';
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.style.borderColor = 'var(--border-glass)';
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-glass)';
        if (e.dataTransfer.files.length) {
            resumeUpload.files = e.dataTransfer.files;
            updateFileName();
        }
    });
    resumeUpload.addEventListener('change', updateFileName);
}

function updateFileName() {
    if (resumeUpload.files.length) {
        fileNameLabel.innerText = `Selected: ${resumeUpload.files[0].name}`;
    } else {
        fileNameLabel.innerText = '';
    }
}

// 1. Submit Candidate Form
candidateForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(candidateForm);
    
    // Add file if dropzone uploaded
    if (resumeUpload.files.length > 0) {
        formData.set('resume', resumeUpload.files[0]);
    } else {
        alert('Please upload a resume PDF.');
        return;
    }
    
    const saveBtn = document.getElementById('saveProfileBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Parsing Resume...';
    
    try {
        const response = await fetch('/api/candidate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to save profile');
        }
        
        const data = await response.json();
        candidateId = data.id;
        
        // Autofill any parsed values if they weren't in form
        document.getElementById('candName').value = data.name;
        document.getElementById('candPhone').value = data.phone;
        document.getElementById('candCurrentCtc').value = data.current_ctc;
        document.getElementById('candExpectedCtc').value = data.expected_ctc;
        document.getElementById('candNotice').value = data.notice_period;
        document.getElementById('candSkills').value = data.skills;
        
        alert(`Candidate profile successfully saved for ${data.name}!`);
        
        // Enable Job panel
        jobCard.classList.remove('disabled-card');
        
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save & Parse Profile';
    }
});

// 2. Scrape JD URL Details
scrapeBtn.addEventListener('click', async () => {
    const url = jdUrlInput.value.trim();
    if (!url) {
        alert('Please enter a Job Description URL first.');
        return;
    }
    
    scrapeBtn.disabled = true;
    scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    
    try {
        const formData = new FormData();
        formData.append('candidate_id', candidateId);
        formData.append('jd_url', url);
        
        const response = await fetch('/api/job', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Scraping failed');
        
        const data = await response.json();
        currentJobId = data.id;
        
        companyNameInput.value = data.company_name;
        jobTitleInput.value = data.job_title;
        jdTextInput.value = data.jd_url ? data.jd_text : jdTextInput.value;
        hrPhoneInput.value = data.hr_phone || hrPhoneInput.value;
        
        alert(`Scraped ${data.company_name} successfully! Match Score: ${data.fit_score}/10`);
        
    } catch (err) {
        alert('Error scraping URL. Please enter job description text manually.');
    } finally {
        scrapeBtn.disabled = false;
        scrapeBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Scrape';
    }
});

// 3. Submit Job details & Dial call
jobForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!candidateId) {
        alert('Please save candidate profile first.');
        return;
    }
    
    const startCallBtn = document.getElementById('startCallBtn');
    startCallBtn.disabled = true;
    startCallBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dialing...';
    
    try {
        // Step A: Save Job (if not saved via Scrape)
        const jobFormData = new FormData();
        jobFormData.append('candidate_id', candidateId);
        jobFormData.append('company_name', companyNameInput.value);
        jobFormData.append('job_title', jobTitleInput.value);
        jobFormData.append('jd_text', jdTextInput.value);
        jobFormData.append('hr_phone', hrPhoneInput.value);
        if (jdUrlInput.value) {
            jobFormData.append('jd_url', jdUrlInput.value);
        }
        
        const jobRes = await fetch('/api/job', {
            method: 'POST',
            body: jobFormData
        });
        if (!jobRes.ok) throw new Error('Failed to register job description.');
        const jobData = await jobRes.json();
        currentJobId = jobData.id;
        
        // Step B: Initiate Call
        const callFormData = new FormData();
        callFormData.append('job_id', currentJobId);
        callFormData.append('hr_phone', hrPhoneInput.value);
        
        const callRes = await fetch('/api/call', {
            method: 'POST',
            body: callFormData
        });
        
        if (!callRes.ok) {
            const err = await callRes.json();
            throw new Error(err.error || 'Failed to connect telephony');
        }
        
        const callData = await callRes.json();
        activeCallId = callData.call_id;
        
        // Transition terminal screen
        terminalScreen.innerHTML = '';
        appendTerminalMessage('system', `Status: Dialing ${hrPhoneInput.value}...`);
        
        // Check if call is Mock
        if (callData.status === 'MOCK_DIALING') {
            updateCallIndicator('dialing');
            simulatorArea.style.display = 'flex';
            setupCallWebSocket(activeCallId);
        } else {
            updateCallIndicator('dialing');
            // For real calls, we listen to updates via WebSocket
            setupCallWebSocket(activeCallId);
        }
        
    } catch (err) {
        alert('Call failed: ' + err.message);
        startCallBtn.disabled = false;
        startCallBtn.innerHTML = '<i class="fa-solid fa-phone-volume"></i> Initiate Outbound Call';
    }
});

// WebSocket Handler for Live dialogue updates
function setupCallWebSocket(callId) {
    if (wsConn) {
        wsConn.close();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/call/${callId}`;
    
    wsConn = new WebSocket(wsUrl);
    
    wsConn.onopen = () => {
        console.log('Call state machine WebSocket opened.');
    };
    
    wsConn.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        
        if (msg.role === 'agent') {
            updateCallIndicator('active');
            appendTerminalMessage('agent', msg.content);
        } else if (msg.role === 'hr') {
            appendTerminalMessage('hr', msg.content);
        } else if (msg.role === 'system') {
            appendTerminalMessage('system', msg.content);
            
            // Check terminal codes
            if (msg.content.includes('warm-transferred') || msg.content.includes('Call successfully')) {
                updateCallIndicator('transferred');
                endCallSession();
            } else if (msg.content.includes('completed') || msg.content.includes('finished')) {
                updateCallIndicator('idle');
                endCallSession();
            }
        }
    };
    
    wsConn.onclose = () => {
        console.log('Call state machine WebSocket closed.');
        endCallSession();
    };
    
    wsConn.onerror = (e) => {
        console.error('WebSocket Error: ', e);
    };
}

// Simulated HR Message sender
simulatorSendBtn.addEventListener('click', sendSimulatedResponse);
simulatorInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendSimulatedResponse();
});

function sendSimulatedResponse() {
    const text = simulatorInput.value.trim();
    if (!text || !wsConn) return;
    
    // Echo locally immediately (onmessage handles broadcast too, but let's keep clean)
    wsConn.send(JSON.stringify({ content: text }));
    simulatorInput.value = '';
}

// Helpers
function appendTerminalMessage(role, text) {
    const turnDiv = document.createElement('div');
    turnDiv.classList.add('chat-turn', `${role}-turn`);
    
    let headerText = '';
    if (role === 'agent') headerText = 'Agent Pitch';
    else if (role === 'hr') headerText = 'HR Representative';
    else if (role === 'system') headerText = 'System Event';
    
    turnDiv.innerHTML = `
        <div class="turn-header">${headerText}</div>
        <div class="turn-content">${text}</div>
    `;
    
    terminalScreen.appendChild(turnDiv);
    terminalScreen.scrollTop = terminalScreen.scrollHeight;
}

function updateCallIndicator(status) {
    callStatusBadge.className = 'call-indicator';
    if (status === 'idle') {
        callStatusBadge.innerText = 'Idle';
    } else if (status === 'dialing') {
        callStatusBadge.classList.add('call-dialing');
        callStatusBadge.innerText = 'Dialing HR';
    } else if (status === 'active') {
        callStatusBadge.classList.add('call-active');
        callStatusBadge.innerText = 'In Call';
    } else if (status === 'transferred') {
        callStatusBadge.classList.add('call-transferred');
        callStatusBadge.innerText = 'Transferred';
    }
}

function endCallSession() {
    simulatorArea.style.display = 'none';
    const startCallBtn = document.getElementById('startCallBtn');
    startCallBtn.disabled = false;
    startCallBtn.innerHTML = '<i class="fa-solid fa-phone-volume"></i> Initiate Outbound Call';
    loadCallHistory();
}

// 4. Call History Logs Loader
async function loadCallHistory() {
    try {
        const response = await fetch('/api/calls');
        if (!response.ok) throw new Error();
        const calls = await response.json();
        
        if (calls.length === 0) {
            historyTableBody.innerHTML = '<tr><td colspan="7" class="empty-state">No call logs recorded yet.</td></tr>';
            return;
        }
        
        historyTableBody.innerHTML = '';
        calls.forEach(call => {
            const tr = document.createElement('tr');
            
            // Format status badge
            let badgeClass = 'badge-primary';
            if (call.status === 'COMPLETED') badgeClass = 'badge-success';
            if (call.status === 'TRANSFERRED') badgeClass = 'badge-success';
            if (call.status === 'FAILED') badgeClass = 'badge-warning';
            
            const callbackTime = call.scheduled_callback ? call.scheduled_callback : '-';
            
            tr.innerHTML = `
                <td><strong>${call.candidate_name || 'Candidate'}</strong></td>
                <td>${call.company_name}</td>
                <td>${call.job_title}</td>
                <td><code>${call.hr_phone}</code></td>
                <td><span class="badge ${badgeClass}">${call.status}</span></td>
                <td>${callbackTime}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="viewTranscript('${call.id}')">
                        <i class="fa-solid fa-file-text"></i> View Transcript
                    </button>
                </td>
            `;
            historyTableBody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load call logs: ', err);
    }
}

// Modal View details
async function viewTranscript(callId) {
    try {
        const response = await fetch('/api/calls');
        if (!response.ok) return;
        const calls = await response.json();
        const call = calls.find(c => c.id === callId);
        
        if (call) {
            transcriptBox.innerText = call.transcript || 'No transcript generated.';
            transcriptModal.classList.add('active');
        }
    } catch (e) {
        console.error(e);
    }
}

modalCloseBtn.addEventListener('click', () => {
    transcriptModal.classList.remove('active');
});

transcriptModal.addEventListener('click', (e) => {
    if (e.target === transcriptModal) {
        transcriptModal.classList.remove('active');
    }
});
