import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from './api/client';
import type { ApprovalRow, AuditResult, CandidateRow, DigestRow, MessageRow, Overview, SupportAnswer, TicketRow, WorkflowIntakeResponse } from './types';

const navigation = [
  { id: 'Overview', label: "Vue d'ensemble", icon: 'OV' },
  { id: 'Workflow', label: 'Demande IA', icon: 'IA' },
  { id: 'Inbox', label: 'Boîte de réception', icon: 'IN' },
  { id: 'Candidates', label: 'Candidats', icon: 'CA' },
  { id: 'Approvals', label: 'Approbations', icon: 'AP' },
  { id: 'Digest', label: 'Brief RH', icon: 'BR' },
  { id: 'Support', label: 'Assistant RH', icon: 'RH' },
  { id: 'Tickets', label: 'Demandes RH', icon: 'TK' },
  { id: 'Audit', label: 'Audit', icon: 'AU' },
];

type SessionUser = {
  id: number;
  email: string;
  role: string;
  department: string | null;
  full_name: string;
};

type CandidateDetails = CandidateRow & {
  source?: string;
  application_status?: string;
  breakdown?: Record<string, number>;
  missing?: string[];
  evidence?: Array<{ source: string; text: string }>;
  reviewed_by?: string;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Une erreur inattendue est survenue.';
}

function formatRole(role: string): string {
  const labels: Record<string, string> = {
    ADMIN: 'Administrateur',
    EMPLOYEE: 'Collaborateur',
    HR: 'Équipe RH',
    HR_MANAGER: 'Responsable RH',
    RECRUITER: 'Recruteur',
  };
  return labels[role.toUpperCase()] || role.replace(/_/g, ' ').toLowerCase();
}

function formatApprovalAction(action: string): string {
  const labels: Record<string, string> = {
    SEND_INTERVIEW_INVITE: 'Envoyer une invitation à un entretien',
  };
  return labels[action] || action.replace(/_/g, ' ').toLowerCase();
}

function formatCandidateStatus(status?: string): string {
  if (!status) return 'Profil évalué';
  const labels: Record<string, string> = {
    AWAITING_CANDIDATE: 'En attente du candidat',
    HIRED: 'Recruté',
    NEW: 'Nouveau',
    REJECTED: 'Refusé',
    SCREENING: 'À évaluer',
  };
  return labels[status.toUpperCase()] || status.replace(/_/g, ' ').toLowerCase();
}

function formatBreakdownLabel(key: string): string {
  const labels: Record<string, string> = {
    ATS_AGENT: 'Équipe recrutement',
    EMPLOYEE_SUPPORT: 'Support collaborateurs',
    HUMAN_REVIEW: 'Revue humaine',
    EMPLOYEE: 'Support collaborateurs',
    EMPLOYEE_AGENT: 'Support collaborateurs',
    NEW_APPLICATION: 'Nouvelle candidature',
    OTHER: 'Autre demande',
    POLICY_QA: 'Question sur une politique RH',
    RECRUITMENT: 'Recrutement',
    URGENT_AGENT: 'Équipe RH urgente',
    TRAINING_REQUEST: 'Demande de formation',
    IT_ACCESS_REQUEST: 'Demande d’accès informatique',
    TRAINING: 'Formation',
    DEPARTMENT_REQUEST: 'Demande de service',
    HR: 'Ressources humaines',
    IT: 'Informatique',
    certifications: 'Certifications',
    education: 'Formation',
    experience: 'Expérience',
    projects: 'Projets',
    skills: 'Compétences',
  };
  return labels[key.toUpperCase()] || labels[key.toLowerCase()] || key.replace(/_/g, ' ').toLowerCase();
}

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('easeit_token'));
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loginForm, setLoginForm] = useState({ email: 'recruiter@easeit.local', password: 'recruiter123' });
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('Overview');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [messages, setMessages] = useState<MessageRow[]>([]);
  const [candidates, setCandidates] = useState<CandidateRow[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRow[]>([]);
  const [digest, setDigest] = useState<DigestRow[]>([]);
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const [busyApproval, setBusyApproval] = useState<number | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateDetails | null>(null);
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [supportQuestion, setSupportQuestion] = useState('');
  const [supportAnswer, setSupportAnswer] = useState<SupportAnswer | null>(null);
  const [supportLoading, setSupportLoading] = useState(false);
  const [tickets, setTickets] = useState<TicketRow[]>([]);
  const [busyTicket, setBusyTicket] = useState<number | null>(null);
  const [workflowForm, setWorkflowForm] = useState({ subject: '', body: '', cv_text: '', candidate_name: '', job_id: 'JOB-001' });
  const [workflowCvFile, setWorkflowCvFile] = useState<File | null>(null);
  const [workflowResult, setWorkflowResult] = useState<WorkflowIntakeResponse | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowRequestKey, setWorkflowRequestKey] = useState(() => crypto.randomUUID());

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setPageError('');
    try {
      let sessionRole = user?.role;
      if (!sessionRole) {
        const storedUser = localStorage.getItem('easeit_user');
        if (storedUser) {
          try {
            sessionRole = (JSON.parse(storedUser) as SessionUser).role;
          } catch {
            localStorage.removeItem('easeit_user');
          }
        }
      }
      const employeeSession = sessionRole === 'EMPLOYEE';
      const [overviewData, messageData, candidateData, approvalData, digestData, auditData, ticketData] = await Promise.all([
        apiFetch<Overview>('/api/overview'),
        employeeSession ? Promise.resolve([] as MessageRow[]) : apiFetch<MessageRow[]>('/api/messages'),
        employeeSession ? Promise.resolve([] as CandidateRow[]) : apiFetch<CandidateRow[]>('/api/candidates'),
        employeeSession ? Promise.resolve([] as ApprovalRow[]) : apiFetch<ApprovalRow[]>('/api/approvals'),
        employeeSession ? Promise.resolve([] as DigestRow[]) : apiFetch<DigestRow[]>('/api/digest'),
        employeeSession ? Promise.resolve(null as AuditResult | null) : apiFetch<AuditResult>('/api/audit/verify'),
        apiFetch<TicketRow[]>('/api/tickets'),
      ]);
      setOverview(overviewData);
      setMessages(messageData);
      setCandidates(candidateData);
      setApprovals(approvalData);
      setDigest(digestData);
      setAudit(auditData);
      setTickets(ticketData);
    } catch (error) {
      setPageError(`Impossible de charger les données. ${getErrorMessage(error)}`);
    } finally {
      setLoading(false);
    }
  }, [user?.role]);

  useEffect(() => {
    if (!token) return;
    try {
      const storedUser = localStorage.getItem('easeit_user');
      setUser(storedUser ? (JSON.parse(storedUser) as SessionUser) : null);
    } catch {
      localStorage.removeItem('easeit_user');
      setUser(null);
    }
    void fetchDashboard();
  }, [token, fetchDashboard]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(''), 3500);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  useEffect(() => {
    if (!selectedCandidate) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSelectedCandidate(null);
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [selectedCandidate]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      const result = await apiFetch<{ access_token: string; user: SessionUser }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm),
      });
      localStorage.setItem('easeit_token', result.access_token);
      localStorage.setItem('easeit_user', JSON.stringify(result.user));
      setUser(result.user);
      setToken(result.access_token);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('easeit_token');
    localStorage.removeItem('easeit_user');
    setToken(null);
    setUser(null);
    setActiveTab('Overview');
    setOverview(null);
    setMessages([]);
    setCandidates([]);
    setApprovals([]);
    setDigest([]);
    setAudit(null);
    setTickets([]);
    setSelectedCandidate(null);
    setSupportQuestion('');
    setSupportAnswer(null);
    setSearch('');
    setPageError('');
    setNotice('');
  };

  const handleApproval = async (approval: ApprovalRow, decision: 'approve' | 'reject') => {
    setBusyApproval(approval.id);
    setPageError('');
    try {
      await apiFetch<{ status: string; approval_id: number }>(`/api/approvals/${approval.id}/${decision}`, {
        method: 'POST',
      });
      setNotice(decision === 'approve'
        ? 'Brouillon approuvé. Aucun courriel n’a été envoyé.'
        : 'Brouillon refusé. Aucun courriel n’a été envoyé.');
      await fetchDashboard();
    } catch (error) {
      await fetchDashboard();
      setPageError(`L'approbation n'a pas pu être enregistrée. ${getErrorMessage(error)}`);
    } finally {
      setBusyApproval(null);
    }
  };

  const openCandidate = async (candidate: CandidateRow) => {
    setSelectedCandidate(candidate);
    setCandidateLoading(true);
    try {
      const details = await apiFetch<CandidateDetails>(`/api/candidates/${encodeURIComponent(candidate.id)}`);
      setSelectedCandidate(details);
    } catch (error) {
      setPageError(`Impossible de charger le profil candidat. ${getErrorMessage(error)}`);
    } finally {
      setCandidateLoading(false);
    }
  };

  const handleSupportQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPageError('');
    setSupportLoading(true);
    setSupportAnswer(null);
    try {
      const answer = await apiFetch<SupportAnswer>('/api/support', {
        method: 'POST',
        body: JSON.stringify({ question: supportQuestion }),
      });
      setSupportAnswer(answer);
      setSupportQuestion('');
      if (answer.escalated) {
        setNotice(answer.ticket_id
          ? `Votre demande a été transmise à l’équipe RH · Référence #${answer.ticket_id}.`
          : 'Votre demande a été transmise à l’équipe RH.');
        await fetchDashboard();
      }
    } catch (error) {
      setPageError(`Impossible d'envoyer votre question. ${getErrorMessage(error)}`);
    } finally {
      setSupportLoading(false);
    }
  };

  const handleTicketStatus = async (ticket: TicketRow, status: 'IN_PROGRESS' | 'RESOLVED') => {
    setBusyTicket(ticket.id);
    setPageError('');
    try {
      await apiFetch<{ id: number; status: string }>(`/api/tickets/${ticket.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      setNotice(status === 'RESOLVED' ? 'Demande marquée comme traitée.' : 'Demande prise en charge.');
      await fetchDashboard();
    } catch (error) {
      setPageError(`Impossible de mettre à jour la demande. ${getErrorMessage(error)}`);
    } finally {
      setBusyTicket(null);
    }
  };

  const updateWorkflowForm = (updates: Partial<typeof workflowForm>) => {
    setWorkflowForm((current) => ({ ...current, ...updates }));
    setWorkflowResult(null);
    setWorkflowRequestKey(crypto.randomUUID());
  };

  const handleWorkflowSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPageError('');
    setWorkflowLoading(true);
    try {
      const headers = { 'Idempotency-Key': workflowRequestKey };
      let result: WorkflowIntakeResponse;
      if (workflowCvFile) {
        const form = new FormData();
        form.set('subject', workflowForm.subject);
        form.set('body', workflowForm.body);
        form.set('candidate_name', workflowForm.candidate_name);
        form.set('job_id', workflowForm.job_id);
        form.set('cv_file', workflowCvFile);
        result = await apiFetch<WorkflowIntakeResponse>('/api/workflows/intake/cv', { method: 'POST', headers, body: form });
      } else {
        result = await apiFetch<WorkflowIntakeResponse>('/api/workflows/intake', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            ...workflowForm,
            body: workflowForm.body.trim() || (workflowForm.cv_text.trim() ? 'Candidature reçue avec CV.' : ''),
          }),
        });
      }
      setWorkflowResult(result);
      setWorkflowRequestKey(crypto.randomUUID());
      setNotice(result.duplicate ? 'Cette demande avait déjà été traitée.' : 'Demande traitée par n8n et ajoutée à la boîte de réception.');
      await fetchDashboard();
    } catch (error) {
      setPageError(`Le workflow n’a pas pu traiter la demande. ${getErrorMessage(error)}`);
    } finally {
      setWorkflowLoading(false);
    }
  };

  const filteredCandidates = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('fr');
    if (!query) return candidates;
    return candidates.filter((candidate) =>
      `${candidate.full_name} ${candidate.email} ${candidate.id}`.toLocaleLowerCase('fr').includes(query),
    );
  }, [candidates, search]);

  const filteredMessages = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('fr');
    if (!query) return messages;
    return messages.filter((message) =>
      `${message.subject} ${message.sender} ${message.category} ${message.intent}`
        .toLocaleLowerCase('fr')
        .includes(query),
    );
  }, [messages, search]);

  const pendingApprovals = approvals.filter((approval) => approval.status.toUpperCase() === 'PENDING_APPROVAL');
  const expiredApprovalIds = useMemo(() => {
    const expired = new Set<number>();
    approvals.forEach((approval) => {
      if (approval.status.toUpperCase() === 'PENDING_APPROVAL' && approval.expires_at
        && Date.parse(approval.expires_at) <= Date.now()) {
        expired.add(approval.id);
      }
    });
    return expired;
  }, [approvals]);
  const visibleNavigation = navigation.filter((item) => {
    if (user?.role === 'EMPLOYEE') return item.id === 'Overview' || item.id === 'Support';
    if (item.id === 'Support') return false;
    if (item.id === 'Tickets') return true;
    return true;
  });
  const activeNavigation = visibleNavigation.find((item) => item.id === activeTab);
  const today = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());

  if (!token) {
    return (
      <main className="login-layout">
        <section className="login-intro">
          <div className="brand-lockup"><span className="brand-mark">E</span><span>EASEIT</span></div>
          <div className="login-message">
            <span className="overline">L'intelligence RH, simplement</span>
            <h1>Le travail RH mérite de respirer.</h1>
            <p>Un espace unique pour piloter vos recrutements, vos demandes et vos décisions avec sérénité.</p>
            <div className="login-proof"><span className="proof-dot" /> Vos données restent dans votre espace sécurisé</div>
          </div>
          <span className="login-footnote">EASEIT · Votre espace de travail RH</span>
        </section>
        <section className="login-panel">
          <form className="login-card" onSubmit={handleLogin}>
            <div className="login-mobile-brand"><span className="brand-mark">E</span> EASEIT</div>
            <span className="overline">Bon retour parmi nous</span>
            <h2>Connectez-vous</h2>
            <p className="muted">Accédez à votre espace de pilotage RH.</p>
            <label htmlFor="login-email">Adresse e-mail</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              required
              value={loginForm.email}
              onChange={(event) => setLoginForm((current) => ({ ...current, email: event.target.value }))}
            />
            <label htmlFor="login-password">Mot de passe</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={loginForm.password}
              onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))}
            />
            {loginError && <div className="error-box" role="alert">{loginError}</div>}
            <button type="submit" className="primary-button login-submit" disabled={loginLoading}>
              {loginLoading ? 'Connexion en cours…' : 'Se connecter'} <span aria-hidden="true">→</span>
            </button>
            <div className="demo-hint">
              <span className="hint-label">ACCÈS DÉMO</span>
              <span>recruiter@easeit.local</span>
              <span>Mot de passe : recruiter123</span>
            </div>
          </form>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="#home" onClick={(event) => { event.preventDefault(); setActiveTab('Overview'); }}>
          <span className="brand-mark">E</span><span>EASEIT</span>
        </a>
        <div className="workspace-label">ESPACE DE TRAVAIL</div>
        <nav className="side-navigation" aria-label="Navigation principale">
          {visibleNavigation.map((item) => (
            <button
              key={item.id}
              className={item.id === activeTab ? 'nav-item active' : 'nav-item'}
              onClick={() => { setActiveTab(item.id); setSearch(''); }}
              aria-current={item.id === activeTab ? 'page' : undefined}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              {item.id === 'Approvals' && pendingApprovals.length > 0 && (
                <span className="nav-count">{pendingApprovals.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="secure-note"><span className="secure-dot" /> Espace sécurisé</div>
          <div className="sidebar-profile">
            <div className="avatar">{(user?.full_name || user?.email || 'R').slice(0, 1).toUpperCase()}</div>
            <div className="profile-copy">
              <strong>{user?.full_name || 'Équipe RH'}</strong>
              <span>{user?.role ? formatRole(user.role) : 'Collaborateur'}</span>
            </div>
            <button className="logout-button" onClick={handleLogout} aria-label="Se déconnecter" title="Se déconnecter">↗</button>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb"><span>Votre espace</span><span className="breadcrumb-separator">/</span><strong>{activeNavigation?.label}</strong></div>
          <div className="topbar-right">
            <span className="today-label">{today}</span>
            <button className="refresh-button" onClick={() => void fetchDashboard()} disabled={loading}>
              <span className={loading ? 'refresh-icon spinning' : 'refresh-icon'} aria-hidden="true">↻</span>
              <span className="refresh-label">{loading ? 'Actualisation…' : 'Actualiser'}</span>
            </button>
          </div>
        </header>

        <main className="content">
          {pageError && (
            <div className="notice error-notice" role="alert">
              <span>{pageError}</span>
              <button onClick={() => void fetchDashboard()} disabled={loading}>Réessayer</button>
              <button className="notice-dismiss" onClick={() => setPageError('')} aria-label="Fermer">×</button>
            </div>
          )}
          {notice && <div className="notice success-notice" role="status">{notice}</div>}

          {activeTab === 'Overview' && (
            <>
              <section className="welcome-row">
                <div>
                  <span className="overline">TABLEAU DE BORD · {today.toLocaleUpperCase('fr-FR')}</span>
                  <h1>Bonjour{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''} <span className="wave">✦</span></h1>
                  <p>Voici les sujets qui méritent votre attention aujourd'hui.</p>
                </div>
                {user?.role === 'EMPLOYEE'
                  ? <button className="primary-button" onClick={() => setActiveTab('Support')}>Poser une question RH <span aria-hidden="true">→</span></button>
                  : <button className="primary-button" onClick={() => setActiveTab('Approvals')}>Voir les approbations <span aria-hidden="true">→</span></button>}
              </section>

              <section className="metric-grid" aria-label="Indicateurs clés">
                {user?.role !== 'EMPLOYEE' && (
                  <>
                    <MetricCard label="Candidats" value={overview?.summary.candidates} note="dans le vivier" icon="CA" tone="blue" onClick={() => setActiveTab('Candidates')} />
                    <MetricCard label="Messages reçus" value={overview?.summary.messages} note="dans la boîte RH" icon="IN" tone="violet" onClick={() => setActiveTab('Inbox')} />
                    <MetricCard label="À approuver" value={overview?.summary.pending_approvals} note="en attente de décision" icon="AP" tone="amber" onClick={() => setActiveTab('Approvals')} />
                  </>
                )}
                <MetricCard label={user?.role === 'EMPLOYEE' ? 'Mes demandes en cours' : 'Tickets ouverts'} value={overview?.summary.open_tickets} note={user?.role === 'EMPLOYEE' ? 'demandes transmises à RH' : 'demandes collaborateurs'} icon="RH" tone="green" onClick={() => setActiveTab(user?.role === 'EMPLOYEE' ? 'Support' : 'Tickets')} />
              </section>

              {user?.role === 'EMPLOYEE' ? (
                <section className="employee-home-panel">
                  <div className="support-icon">RH</div>
                  <div><span className="overline">BESOIN D’AIDE ?</span><h2>Votre espace RH, en toute simplicité</h2><p>Posez une question sur les politiques RH ou consultez le suivi de vos demandes déjà transmises.</p></div>
                  <button className="text-button" onClick={() => setActiveTab('Support')}>Accéder à l’assistant RH <span aria-hidden="true">→</span></button>
                </section>
              ) : <section className="overview-grid">
                <div className="panel">
                  <div className="panel-heading">
                    <div><span className="overline">À TRAITER</span><h2>Approbations en attente</h2></div>
                    <button className="text-button" onClick={() => setActiveTab('Approvals')}>Tout voir <span aria-hidden="true">→</span></button>
                  </div>
                  {pendingApprovals.length ? (
                    <div className="compact-list">
                      {pendingApprovals.slice(0, 3).map((approval) => (
                        <div className="compact-row" key={approval.id}>
                          <span className="list-symbol amber-symbol">AP</span>
                          <div className="compact-copy"><strong>{formatApprovalAction(approval.action)}</strong><span>Validation requise · {formatRole(approval.required_role)}</span></div>
                          <button className="subtle-button" onClick={() => setActiveTab('Approvals')}>Examiner</button>
                        </div>
                      ))}
                    </div>
                  ) : <EmptyState title="Tout est à jour" detail="Aucune approbation ne requiert votre attention." />}
                </div>
                <div className="panel">
                  <div className="panel-heading">
                    <div><span className="overline">RÉCENT</span><h2>Derniers messages</h2></div>
                    <button className="text-button" onClick={() => setActiveTab('Inbox')}>Ouvrir la boîte <span aria-hidden="true">→</span></button>
                  </div>
                  {messages.length ? (
                    <div className="compact-list">
                      {messages.slice(0, 3).map((message) => (
                        <div className="compact-row" key={message.id}>
                          <span className="sender-avatar">{message.sender.slice(0, 1).toUpperCase()}</span>
                          <div className="compact-copy"><strong>{message.subject}</strong><span>{message.sender}</span></div>
                          <PriorityBadge priority={message.priority} />
                        </div>
                      ))}
                    </div>
                  ) : <EmptyState title="Aucun message" detail="Les nouveaux messages apparaîtront ici." />}
                </div>
              </section>}

              {user?.role !== 'EMPLOYEE' && <section className="system-footer">
                <span className={audit?.valid ? 'system-indicator' : 'system-indicator warning'} />
                <span>{audit?.valid ? 'Journal d’audit vérifié' : audit ? 'Vérification du journal à contrôler' : 'État du journal indisponible'}</span>
                <button className="text-button" onClick={() => setActiveTab('Audit')}>Consulter <span aria-hidden="true">→</span></button>
              </section>}
            </>
          )}

          {activeTab === 'Workflow' && user?.role !== 'EMPLOYEE' && (
            <>
              <PageHeading
                eyebrow="ORCHESTRATION LOCALE"
                title="Nouvelle demande RH"
                detail="Le backend authentifie votre session, transmet la demande au workflow n8n et enregistre sa classification dans la boîte de réception."
              />
              <section className="workflow-layout">
                <form className="workflow-form" onSubmit={(event) => void handleWorkflowSubmit(event)}>
                  <div className="workflow-form-heading">
                    <span className="workflow-icon">IA</span>
                    <div><strong>Analyser une demande</strong><p>Les actions sensibles restent soumises à une validation humaine.</p></div>
                  </div>
                  <label htmlFor="workflow-subject">Objet</label>
                  <input
                    id="workflow-subject"
                    required
                    maxLength={200}
                    value={workflowForm.subject}
                    onChange={(event) => updateWorkflowForm({ subject: event.target.value })}
                    placeholder="Ex. Demande de report d’entretien"
                  />
                  <label htmlFor="workflow-body">Message</label>
                  <textarea
                    id="workflow-body"
                    required={!workflowCvFile && !workflowForm.cv_text.trim()}
                    maxLength={20000}
                    rows={4}
                    value={workflowForm.body}
                    onChange={(event) => updateWorkflowForm({ body: event.target.value })}
                    placeholder="Décrivez la demande à traiter…"
                  />
                  <details className="workflow-optional-fields">
                    <summary>Informations de candidature (facultatif)</summary>
                    <div className="workflow-optional-grid">
                      <label htmlFor="workflow-candidate">Nom du candidat
                        <input
                          id="workflow-candidate"
                          maxLength={60}
                          value={workflowForm.candidate_name}
                          onChange={(event) => updateWorkflowForm({ candidate_name: event.target.value })}
                        />
                      </label>
                      <label htmlFor="workflow-job">Référence du poste
                        <input
                          id="workflow-job"
                          maxLength={20}
                          value={workflowForm.job_id}
                          onChange={(event) => updateWorkflowForm({ job_id: event.target.value })}
                        />
                      </label>
                    </div>
                    <label htmlFor="workflow-cv-file">CV au format PDF
                      <input
                        id="workflow-cv-file"
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={(event) => {
                          setWorkflowCvFile(event.target.files?.[0] || null);
                          setWorkflowResult(null);
                          setWorkflowRequestKey(crypto.randomUUID());
                        }}
                      />
                    </label>
                    {workflowCvFile && <p className="workflow-file-name">Fichier sélectionné : <strong>{workflowCvFile.name}</strong></p>}
                    <label htmlFor="workflow-cv">Ou coller le texte du CV
                      <textarea
                        id="workflow-cv"
                        maxLength={12000}
                        rows={5}
                        value={workflowForm.cv_text}
                        onChange={(event) => updateWorkflowForm({ cv_text: event.target.value })}
                        placeholder="Collez le texte du CV pour lancer l’analyse ATS…"
                      />
                    </label>
                    <p className="workflow-hint">PDF textuels jusqu’à 5 Mo et 30 pages. Les PDF scannés sans texte sélectionnable nécessitent un traitement OCR non inclus.</p>
                  </details>
                  <div className="workflow-form-footer">
                    <span>Connexion serveur-à-serveur sécurisée · Aucun jeton n8n exposé au navigateur</span>
                    <button className="primary-button" type="submit" disabled={workflowLoading || !workflowForm.subject.trim() || (!workflowForm.body.trim() && !workflowForm.cv_text.trim() && !workflowCvFile)}>
                      {workflowLoading ? 'Analyse en cours…' : 'Lancer le workflow'} <span aria-hidden="true">→</span>
                    </button>
                  </div>
                </form>

                {workflowResult ? (
                  <article className="workflow-result" aria-live="polite">
                    <div className="workflow-result-heading">
                      <span className="workflow-result-icon">✓</span>
                      <div><span className="overline">TRAITEMENT ACCEPTÉ</span><h2>Classification reçue</h2></div>
                    </div>
                    <div className="workflow-result-grid">
                      <div><span>Catégorie</span><strong>{formatBreakdownLabel(workflowResult.classification.category)}</strong></div>
                      <div><span>Priorité</span><strong><PriorityBadge priority={workflowResult.classification.priority} /></strong></div>
                      <div><span>Destination</span><strong>{formatBreakdownLabel(workflowResult.classification.destination)}</strong></div>
                      <div><span>Confiance</span><strong>{Math.round(workflowResult.classification.confidence * 100)}%</strong></div>
                    </div>
                    <p className="workflow-reason">{workflowResult.classification.reason || 'Aucun détail complémentaire fourni.'}</p>
                    {workflowResult.classification.department && <p className="workflow-department">Service : <strong>{workflowResult.classification.department}</strong></p>}
                    <div className="workflow-identifiers">
                      <span>Message <code>{workflowResult.message_id}</code></span>
                      <span>Exécution n8n <code>{workflowResult.execution_id || 'non fournie'}</code></span>
                    </div>
                    {workflowResult.classification.destination === 'HUMAN_REVIEW' && (
                      <p className="workflow-review-note">Cette demande nécessite une revue humaine. Elle est visible dans la boîte de réception.</p>
                    )}
                    <button className="text-button" onClick={() => setActiveTab('Inbox')}>Ouvrir la boîte de réception <span aria-hidden="true">→</span></button>
                  </article>
                ) : (
                  <aside className="workflow-aside">
                    <span className="workflow-aside-glow" aria-hidden="true" />
                    <span className="overline">EASEIT · N8N · OLLAMA</span>
                    <h2>Une orchestration, des décisions maîtrisées.</h2>
                    <p>La classification et les garde-fous du workflow sont conservés. Le résultat est enregistré avec les messages RH existants.</p>
                    <div className="workflow-step"><span>01</span><div><strong>Vérification d’accès</strong><small>JWT EASEIT côté backend</small></div></div>
                    <div className="workflow-step"><span>02</span><div><strong>Analyse locale</strong><small>Workflow n8n et modèle Ollama</small></div></div>
                    <div className="workflow-step"><span>03</span><div><strong>Suivi centralisé</strong><small>Résultat visible dans la boîte RH</small></div></div>
                  </aside>
                )}
              </section>
            </>
          )}

          {activeTab === 'Support' && user?.role === 'EMPLOYEE' && (
            <>
              <PageHeading eyebrow="ESPACE COLLABORATEUR" title="Assistant RH" detail="Posez une question sur les informations RH disponibles. Si une vérification est nécessaire, votre demande est transmise à l’équipe." />
              <section className="support-layout">
                <div className="support-intro">
                  <span className="support-icon">RH</span>
                  <div><strong>Comment puis-je vous aider ?</strong><p>Les réponses s’appuient sur les informations RH de démonstration. Votre solde personnel n’est pas accessible dans cet espace.</p></div>
                </div>
                <div className="support-prompts">
                  <span className="overline">QUESTIONS FRÉQUENTES</span>
                  <div>
                    <button type="button" className="prompt-chip" onClick={() => setSupportQuestion('Quelle est la politique de congés annuelle ?')}>Politique de congés</button>
                    <button type="button" className="prompt-chip" onClick={() => setSupportQuestion('Comment fonctionne le télétravail ?')}>Télétravail</button>
                  </div>
                </div>
                <form className="support-form" onSubmit={(event) => void handleSupportQuestion(event)}>
                  <label htmlFor="support-question">Votre question</label>
                  <textarea
                    id="support-question"
                    rows={4}
                    maxLength={2000}
                    required
                    value={supportQuestion}
                    onChange={(event) => setSupportQuestion(event.target.value)}
                    placeholder="Ex. Quelle est la politique de congés annuelle ?"
                  />
                  <div className="support-form-footer">
                    <span>{supportQuestion.length}/2000 caractères</span>
                    <button className="primary-button" type="submit" disabled={supportLoading || !supportQuestion.trim()}>
                      {supportLoading ? 'Recherche en cours…' : 'Envoyer la question'} <span aria-hidden="true">→</span>
                    </button>
                  </div>
                </form>
                {supportAnswer && (
                  <article className={supportAnswer.escalated ? 'support-answer escalated' : 'support-answer'}>
                    <div className="answer-heading">
                      <span className="answer-status-icon">{supportAnswer.escalated ? '↗' : '✓'}</span>
                      <div><span className="overline">{supportAnswer.escalated ? 'TRANSMISE À L’ÉQUIPE RH' : 'RÉPONSE RH'}</span><strong>{supportAnswer.escalated ? 'Une personne va prendre le relais' : 'Réponse basée sur la politique RH'}</strong></div>
                    </div>
                    <p>{supportAnswer.answer}</p>
                    {supportAnswer.sources.length > 0 && <div className="answer-sources">Source{supportAnswer.sources.length > 1 ? 's' : ''} : {supportAnswer.sources.join(' · ')}</div>}
                    {supportAnswer.ticket_id && <div className="ticket-reference">Votre demande porte la référence <strong>#{supportAnswer.ticket_id}</strong>.</div>}
                  </article>
                )}
                <section className="my-tickets">
                  <div className="panel-heading">
                    <div><span className="overline">SUIVI</span><h2>Mes demandes RH</h2></div>
                    <span className="count-chip">{tickets.length} demande{tickets.length === 1 ? '' : 's'}</span>
                  </div>
                  {tickets.length ? tickets.map((ticket) => (
                    <article className="employee-ticket" key={ticket.id}>
                      <div><strong>{ticket.subject}</strong><p>{ticket.body}</p></div>
                      <StatusBadge status={ticket.status} />
                    </article>
                  )) : <EmptyState title="Aucune demande en cours" detail="Les questions transmises à l’équipe RH apparaîtront ici." />}
                </section>
              </section>
            </>
          )}

          {activeTab === 'Tickets' && user?.role !== 'EMPLOYEE' && (
            <>
              <PageHeading eyebrow="SUIVI RH" title="Demandes collaborateurs" detail="Prenez en charge les demandes transmises à l’équipe et suivez leur résolution." count={`${tickets.filter((ticket) => ticket.status !== 'RESOLVED').length} à traiter`} />
              <div className="ticket-list">
                {tickets.map((ticket) => (
                  <article className="ticket-card" key={ticket.id}>
                    <div className="ticket-card-icon">RH</div>
                    <div className="ticket-content">
                      <div className="ticket-title-row"><h2>{ticket.subject}</h2><StatusBadge status={ticket.status} /></div>
                      <p className="ticket-requester">{ticket.employee_name} · <a href={`mailto:${ticket.employee_email}`}>{ticket.employee_email}</a></p>
                      <p className="ticket-body">{ticket.body}</p>
                      <span className="ticket-assignee">Assignée à {formatRole(ticket.assigned_to || 'HR_MANAGER')} · Réf. #{ticket.id}</span>
                    </div>
                    {ticket.status !== 'RESOLVED' && (
                      <div className="ticket-actions">
                        {ticket.status !== 'IN_PROGRESS' && <button className="subtle-button" onClick={() => void handleTicketStatus(ticket, 'IN_PROGRESS')} disabled={busyTicket === ticket.id}>{busyTicket === ticket.id ? 'Mise à jour…' : 'Prendre en charge'}</button>}
                        <button className="primary-button approve-button" onClick={() => void handleTicketStatus(ticket, 'RESOLVED')} disabled={busyTicket === ticket.id}>{busyTicket === ticket.id ? 'Mise à jour…' : 'Marquer traité'}</button>
                      </div>
                    )}
                  </article>
                ))}
                {!tickets.length && <EmptyState title="Aucune demande RH" detail="Les demandes escaladées par les collaborateurs apparaîtront ici." />}
              </div>
            </>
          )}

          {activeTab === 'Inbox' && (
            <PageHeading eyebrow="COMMUNICATIONS" title="Boîte de réception" detail="Tous les messages RH, classés et orientés vers la bonne équipe." count={`${messages.length} message${messages.length === 1 ? '' : 's'}`} />
          )}
          {activeTab === 'Inbox' && (
            <>
              <SearchField value={search} onChange={setSearch} placeholder="Rechercher un message, un expéditeur…" />
              <div className="message-list">
                {filteredMessages.map((message) => (
                  <article className="message-card" key={message.id}>
                    <button className="message-main" onClick={() => setExpandedMessage(expandedMessage === message.id ? null : message.id)} aria-expanded={expandedMessage === message.id}>
                      <span className="sender-avatar large">{message.sender.slice(0, 1).toUpperCase()}</span>
                      <span className="message-copy">
                        <span className="message-topline"><strong>{message.subject}</strong><PriorityBadge priority={message.priority} /></span>
                        <span>{message.sender}</span>
                        <span className="message-category">{formatBreakdownLabel(message.category)}{message.department && <> <span>·</span> {formatBreakdownLabel(message.department)}</>} <span>·</span> {formatBreakdownLabel(message.intent)} <span>·</span> {formatBreakdownLabel(message.destination)}</span>
                      </span>
                      <span className="message-confidence">{Math.round(message.confidence * 100)}%<small>confiance</small></span>
                      <span className="expand-icon" aria-hidden="true">{expandedMessage === message.id ? '−' : '+'}</span>
                    </button>
                    {expandedMessage === message.id && (
                      <div className="message-detail">
                        <p>{message.body || 'Aucun contenu détaillé disponible.'}</p>
                        <div className="classification-note">Classification automatique · Confiance {Math.round(message.confidence * 100)}%</div>
                      </div>
                    )}
                  </article>
                ))}
                {!filteredMessages.length && <EmptyState title="Aucun résultat" detail="Essayez avec un autre nom, sujet ou catégorie." />}
              </div>
            </>
          )}

          {activeTab === 'Candidates' && (
            <>
              <PageHeading eyebrow="RECRUTEMENT" title="Candidats" detail="Explorez le vivier et consultez les évaluations assistées." count={`${candidates.length} profil${candidates.length === 1 ? '' : 's'}`} />
              <SearchField value={search} onChange={setSearch} placeholder="Rechercher un candidat ou un e-mail…" />
              <div className="candidate-grid">
                {filteredCandidates.map((candidate) => (
                  <button className="candidate-card" key={candidate.id} onClick={() => void openCandidate(candidate)}>
                    <div className="candidate-card-top">
                      <span className="candidate-avatar">{candidate.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span>
                      <span className="score-pill">{candidate.score}<small>/100</small></span>
                    </div>
                    <strong>{candidate.full_name}</strong>
                    <span className="candidate-email">{candidate.email}</span>
                    <span className="candidate-card-bottom"><span>Évaluation du profil</span><span aria-hidden="true">↗</span></span>
                  </button>
                ))}
                {!filteredCandidates.length && <EmptyState title="Aucun candidat trouvé" detail="Modifiez votre recherche ou vérifiez les données chargées." />}
              </div>
            </>
          )}

          {activeTab === 'Approvals' && (
            <>
              <PageHeading eyebrow="DÉCISIONS RH" title="Centre d’approbation" detail="Examinez le contenu du brouillon avant de prendre une décision. L’approbation ne déclenche pas l’envoi du courriel." count={`${pendingApprovals.length} en attente`} />
              <div className="approval-list">
                {approvals.map((approval) => {
                  const pending = approval.status.toUpperCase() === 'PENDING_APPROVAL';
                  return (
                    <article className="approval-card" key={approval.id}>
                      <div className="approval-icon">✓</div>
                      <div className="approval-content">
                        <div className="approval-title-row">                        <h2>{formatApprovalAction(approval.action)}</h2><StatusBadge status={approval.status} /></div>
                        <p>Approbation requise par <strong>{formatRole(approval.required_role)}</strong></p>
                        {approval.draft && (
                          <section className="draft-preview">
                            <span className="overline">{pending ? 'BROUILLON À EXAMINER' : 'BROUILLON ASSOCIÉ'}</span>
                            <div className="draft-meta"><span>Destinataire</span><strong>{approval.draft.recipient}</strong></div>
                            <div className="draft-meta"><span>Objet</span><strong>{approval.draft.subject}</strong></div>
                            <p>{approval.draft.body}</p>
                          </section>
                        )}
                        {pending && approval.expires_at && (
                          <p className={expiredApprovalIds.has(approval.id) ? 'approval-expiry expired' : 'approval-expiry'}>
                            {expiredApprovalIds.has(approval.id) ? 'Cette demande a expiré.' : `Expire le ${new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(approval.expires_at))}`}
                          </p>
                        )}
                        {!approval.draft && Object.keys(approval.payload).length > 0 && (
                          <dl className="payload-list">
                            {Object.entries(approval.payload).map(([key, value]) => (
                              <div key={key}>                              <dt>{key.replace(/_/g, ' ')}</dt><dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd></div>
                            ))}
                          </dl>
                        )}
                      </div>
                      {pending && (
                        <div className="approval-actions">
                          <button className="subtle-button reject-button" onClick={() => void handleApproval(approval, 'reject')} disabled={busyApproval === approval.id || expiredApprovalIds.has(approval.id)}>
                            Refuser
                          </button>
                          <button className="primary-button approve-button" onClick={() => void handleApproval(approval, 'approve')} disabled={busyApproval === approval.id || expiredApprovalIds.has(approval.id)}>
                            {busyApproval === approval.id ? 'Enregistrement…' : 'Approuver le brouillon'}
                          </button>
                        </div>
                      )}
                    </article>
                  );
                })}
                {!approvals.length && <EmptyState title="Aucune approbation" detail="Les demandes de validation apparaîtront ici." />}
              </div>
            </>
          )}

          {activeTab === 'Digest' && (
            <>
              <PageHeading eyebrow="SYNTHÈSE" title="Brief RH" detail="Un aperçu rapide des points d’attention et de l’activité récente." />
              {digest.length ? (
                <div className="digest-list">
                  {digest.map((entry) => (
                    <article className="digest-card" key={entry.period}>
                      <span className="overline">SYNTHÈSE DU {entry.period}</span>
                      <div className="digest-content" dangerouslySetInnerHTML={{ __html: entry.html }} />
                    </article>
                  ))}
                </div>
              ) : <EmptyState title="Brief indisponible" detail="Aucune synthèse n’a encore été générée." />}
            </>
          )}

          {activeTab === 'Audit' && (
            <>
              <PageHeading eyebrow="TRANSPARENCE" title="Journal d’audit" detail="Vérification de l’intégrité de la chaîne des événements." />
              <section className="audit-card">
                <span className={audit?.valid ? 'audit-icon valid' : 'audit-icon invalid'}>{audit?.valid ? '✓' : '!'}</span>
                <div className="audit-copy">
                  <span className="overline">ÉTAT DE LA CHAÎNE</span>
                  <h2>{audit ? (audit.valid ? 'Intégrité confirmée' : 'Vérification nécessaire') : 'Données indisponibles'}</h2>
                  <p>{audit?.valid ? 'La chaîne de hachage a été vérifiée sans anomalie.' : 'La vérification du journal n’a pas pu être confirmée.'}</p>
                </div>
                <div className="audit-count"><strong>{audit?.count ?? '—'}</strong><span>événements</span></div>
                {audit?.broken_at && <div className="error-box">Anomalie détectée à l’entrée {audit.broken_at}.</div>}
              </section>
            </>
          )}

          {loading && !overview && <div className="loading-bar" role="status">Chargement de votre espace…</div>}
        </main>
      </div>

      {selectedCandidate && (
        <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedCandidate(null); }}>
          <aside className="candidate-drawer" role="dialog" aria-modal="true" aria-labelledby="candidate-drawer-title">
            <div className="drawer-header">
              <span className="overline">PROFIL CANDIDAT</span>
              <button className="close-button" onClick={() => setSelectedCandidate(null)} aria-label="Fermer le profil">×</button>
            </div>
            {candidateLoading ? <div className="loading-bar">Chargement du profil…</div> : (
              <>
                <div className="drawer-profile">
                  <span className="candidate-avatar big">{selectedCandidate.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span>
                  <h2 id="candidate-drawer-title">{selectedCandidate.full_name}</h2>
                  <a href={`mailto:${selectedCandidate.email}`}>{selectedCandidate.email}</a>
                  <span className="status-tag">{formatCandidateStatus(selectedCandidate.application_status)}</span>
                </div>
                <div className="drawer-section">
                  <div className="drawer-score"><div><span className="overline">SCORE DE CORRESPONDANCE</span><strong>{selectedCandidate.score}<small>/100</small></strong></div><div className="score-track"><span style={{ width: `${Math.min(100, Math.max(0, selectedCandidate.score))}%` }} /></div></div>
                </div>
                {selectedCandidate.breakdown && Object.keys(selectedCandidate.breakdown).length > 0 && (
                  <div className="drawer-section"><h3>Détail de l’évaluation</h3>
                    {Object.entries(selectedCandidate.breakdown).map(([key, value]) => (
                      <div className="breakdown-row" key={key}><span>{formatBreakdownLabel(key)}</span><strong>{Math.round(value * 100)}%</strong></div>
                    ))}
                  </div>
                )}
                {selectedCandidate.missing && selectedCandidate.missing.length > 0 && (
                  <div className="drawer-section"><h3>Éléments à vérifier</h3><ul>{selectedCandidate.missing.map((item) => <li key={item}>{item}</li>)}</ul></div>
                )}
                {selectedCandidate.evidence && selectedCandidate.evidence.length > 0 && (
                  <div className="drawer-section"><h3>Éléments relevés</h3>{selectedCandidate.evidence.map((item, index) => <p className="evidence-item" key={`${item.source}-${index}`}><strong>{item.source}</strong> · {item.text}</p>)}</div>
                )}
                <div className="drawer-section reviewer-note">Évaluation relue par : {selectedCandidate.reviewed_by || 'Non renseigné'}</div>
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, note, icon, tone, onClick }: { label: string; value?: number; note: string; icon: string; tone: string; onClick?: () => void }) {
  const content = (
    <>
      <span className={`metric-icon ${tone}`}>{icon}</span>
      <span className="metric-label">{label}</span>
      <strong>{value ?? '—'}</strong>
      <span className="metric-note">{note}</span>
      <span className="metric-arrow" aria-hidden="true">↗</span>
    </>
  );
  return onClick ? <button className="metric-card" onClick={onClick}>{content}</button> : <div className="metric-card static">{content}</div>;
}

function PageHeading({ eyebrow, title, detail, count }: { eyebrow: string; title: string; detail: string; count?: string }) {
  return (
    <section className="page-heading">
      <div><span className="overline">{eyebrow}</span><h1>{title}</h1><p>{detail}</p></div>
      {count && <span className="count-chip">{count}</span>}
    </section>
  );
}

function SearchField({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return (
    <label className="search-field">
      <span aria-hidden="true">⌕</span>
      <input type="search" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      {value && <button type="button" onClick={() => onChange('')} aria-label="Effacer la recherche">×</button>}
    </label>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const normalized = priority.toLowerCase();
  const label = normalized === 'urgent' ? 'Urgent'
    : normalized === 'high' ? 'Prioritaire'
      : normalized === 'medium' ? 'Modérée'
        : normalized === 'low' || normalized === 'information' ? 'Faible' : 'Normal';
  return <span className={`priority-badge ${normalized}`}>{label}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const labels: Record<string, string> = {
    APPROVED: 'Approuvée',
    EXPIRED: 'Expirée',
    IN_PROGRESS: 'En cours',
    OPEN: 'Ouverte',
    PENDING_APPROVAL: 'En attente',
    REJECTED: 'Refusée',
    RESOLVED: 'Traitée',
  };
  const stateClass = normalized === 'APPROVED' || normalized === 'RESOLVED' ? 'approved' : normalized === 'REJECTED' || normalized === 'EXPIRED' ? 'rejected' : 'pending';
  return <span className={`status-badge ${stateClass}`}>{labels[normalized] || status}</span>;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><span className="empty-symbol">—</span><strong>{title}</strong><p>{detail}</p></div>;
}

export default App;
