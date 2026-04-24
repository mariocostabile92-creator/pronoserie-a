// ── legal.js - Pagine Privacy Policy e Termini di Servizio ──

function pagePrivacy(){
  return `<div class="container" style="max-width:800px">
    <h1>Privacy Policy</h1>
    <p class="sub">Ultimo aggiornamento: 7 Aprile 2026</p>
    <div class="card" style="line-height:1.8;font-size:.9rem">
      <h3>1. Titolare del Trattamento</h3>
      <p>Il titolare del trattamento dei dati personali e' MatchIQ, raggiungibile all'indirizzo email: <strong>mario.costabile92@outlook.it</strong></p>

      <h3 style="margin-top:16px">2. Dati Raccolti</h3>
      <p>Raccogliamo i seguenti dati personali:</p>
      <ul style="padding-left:20px;color:var(--muted)">
        <li><strong>Email</strong> - fornita in fase di registrazione</li>
        <li><strong>Password</strong> - conservata in forma criptata (hash bcrypt)</li>
        <li><strong>Piano di abbonamento</strong> - Free o Pro</li>
        <li><strong>Utilizzo API</strong> - numero di pronostici richiesti per giorno</li>
      </ul>

      <h3 style="margin-top:16px">3. Finalita' del Trattamento</h3>
      <p>I dati vengono utilizzati esclusivamente per:</p>
      <ul style="padding-left:20px;color:var(--muted)">
        <li>Gestione dell'account utente e autenticazione</li>
        <li>Erogazione del servizio di pronostici sportivi</li>
        <li>Gestione dell'abbonamento Pro tramite Stripe</li>
        <li>Comunicazioni di servizio (reset password)</li>
      </ul>

      <h3 style="margin-top:16px">4. Conservazione dei Dati</h3>
      <p>I dati sono conservati su server sicuri (PostgreSQL su Neon.tech, infrastruttura AWS in Europa). I dati vengono conservati per tutta la durata dell'account. In caso di cancellazione dell'account, i dati vengono eliminati entro 30 giorni.</p>

      <h3 style="margin-top:16px">5. Condivisione dei Dati</h3>
      <p>I dati personali <strong>non vengono venduti ne' condivisi</strong> con terze parti a scopo di marketing. I dati di pagamento sono gestiti esclusivamente da <strong>Stripe</strong> (PCI DSS compliant) e non transitano sui nostri server.</p>

      <h3 style="margin-top:16px">6. Diritti dell'Utente (GDPR)</h3>
      <p>In conformita' al Regolamento UE 2016/679 (GDPR), l'utente ha diritto a:</p>
      <ul style="padding-left:20px;color:var(--muted)">
        <li><strong>Accesso</strong> - ottenere copia dei propri dati</li>
        <li><strong>Rettifica</strong> - correggere dati inesatti</li>
        <li><strong>Cancellazione</strong> - richiedere l'eliminazione dei dati</li>
        <li><strong>Portabilita'</strong> - ricevere i dati in formato leggibile</li>
        <li><strong>Opposizione</strong> - opporsi al trattamento</li>
      </ul>
      <p>Per esercitare questi diritti, contattare: <strong>mario.costabile92@outlook.it</strong></p>

      <h3 style="margin-top:16px">7. Cookie e Tracciamento</h3>
      <p>MatchIQ <strong>non utilizza cookie di tracciamento</strong> ne' strumenti di profilazione di terze parti. Utilizziamo esclusivamente il localStorage del browser per mantenere la sessione di login dell'utente.</p>

      <h3 style="margin-top:16px">8. Modifiche alla Privacy Policy</h3>
      <p>Ci riserviamo il diritto di modificare questa informativa. Le modifiche saranno pubblicate su questa pagina con la data di aggiornamento.</p>
    </div>
  </div>`;
}

function pageTermini(){
  return `<div class="container" style="max-width:800px">
    <h1>Termini di Servizio</h1>
    <p class="sub">Ultimo aggiornamento: 7 Aprile 2026</p>
    <div class="card" style="line-height:1.8;font-size:.9rem">
      <h3>1. Descrizione del Servizio</h3>
      <p>MatchIQ e' una piattaforma di analisi statistica applicata al calcio. Utilizza algoritmi di intelligenza artificiale (modello Dixon-Coles, distribuzione di Poisson) per generare pronostici sportivi basati su dati storici e dati in tempo reale.</p>

      <h3 style="margin-top:16px">2. Natura del Servizio</h3>
      <div style="background:#1a0a0a;border:1px solid #e74c3c;border-radius:8px;padding:12px;margin:8px 0">
        <p style="color:#e74c3c;font-weight:700">IMPORTANTE</p>
        <p>I pronostici forniti da MatchIQ sono <strong>analisi statistiche a scopo puramente informativo e di intrattenimento</strong>. Non costituiscono in alcun modo:</p>
        <ul style="padding-left:20px;color:#ccc">
          <li>Consulenza finanziaria o di investimento</li>
          <li>Garanzia di vincita</li>
          <li>Invito o incitamento al gioco d'azzardo</li>
          <li>Suggerimento professionale per il gioco d'azzardo</li>
        </ul>
      </div>

      <h3 style="margin-top:16px">3. Limitazione di Responsabilita'</h3>
      <p>MatchIQ <strong>non si assume alcuna responsabilita'</strong> per eventuali perdite economiche derivanti dall'utilizzo dei pronostici forniti. L'utente e' l'unico responsabile delle proprie decisioni relative al gioco d'azzardo.</p>

      <h3 style="margin-top:16px">4. Eta' Minima</h3>
      <p>Il servizio e' riservato a utenti di <strong>eta' pari o superiore a 18 anni</strong>. Registrandosi, l'utente dichiara di avere almeno 18 anni compiuti.</p>

      <h3 style="margin-top:16px">5. Gioco Responsabile</h3>
      <div style="background:#0d1b2a;border-radius:8px;padding:12px;margin:8px 0">
        <p>Il gioco d'azzardo puo' creare <strong>dipendenza patologica</strong>. Se ritieni di avere un problema con il gioco, contatta:</p>
        <ul style="padding-left:20px;color:var(--muted)">
          <li>Numero verde: <strong style="color:#2ecc71">800-558822</strong></li>
          <li>Sito ADM: <a href="https://www.adm.gov.it" target="_blank" style="color:var(--accent)">www.adm.gov.it</a></li>
          <li>Giocatori Anonimi: <a href="https://www.giocatorianonimi.org" target="_blank" style="color:var(--accent)">www.giocatorianonimi.org</a></li>
        </ul>
      </div>

      <h3 style="margin-top:16px">6. Piani e Pagamenti</h3>
      <p><strong>Piano Free:</strong> accesso limitato a 2 pronostici al giorno, gratuito e senza impegno.</p>
      <p><strong>Piano Pro (9.99 EUR/mese):</strong> accesso illimitato a tutte le funzionalita'. L'abbonamento si rinnova automaticamente ogni mese. L'utente puo' cancellare l'abbonamento in qualsiasi momento dalla propria area personale. I pagamenti sono gestiti da Stripe.</p>
      <p><strong>Rimborsi:</strong> e' possibile richiedere un rimborso entro 14 giorni dall'attivazione dell'abbonamento, a condizione che il servizio non sia stato utilizzato in modo significativo.</p>

      <h3 style="margin-top:16px">7. Proprieta' Intellettuale</h3>
      <p>Tutti i contenuti, algoritmi, analisi e il software di MatchIQ sono di proprieta' esclusiva del titolare. E' vietata la riproduzione, distribuzione o rivendita dei pronostici senza autorizzazione scritta.</p>
      <p>I loghi e gli stemmi delle squadre di calcio sono di proprieta' dei rispettivi club e vengono utilizzati a scopo informativo tramite licenza API-Football.</p>

      <h3 style="margin-top:16px">8. Dati e Fonti</h3>
      <p>I dati utilizzati provengono da:</p>
      <ul style="padding-left:20px;color:var(--muted)">
        <li>API-Football (dati ufficiali partite, classifiche, statistiche)</li>
        <li>Football-Data.co.uk (dati storici e quote bookmaker)</li>
        <li>Google News (notizie calcistiche)</li>
      </ul>

      <h3 style="margin-top:16px">9. Legge Applicabile</h3>
      <p>I presenti Termini sono regolati dalla legge italiana. Per qualsiasi controversia sara' competente il Foro di residenza dell'utente consumatore.</p>

      <h3 style="margin-top:16px">10. Contatti</h3>
      <p>Per qualsiasi domanda o richiesta: <strong>mario.costabile92@outlook.it</strong></p>
    </div>
  </div>`;
}
