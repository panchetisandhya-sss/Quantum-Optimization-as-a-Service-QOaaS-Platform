import os
import sys
from odf.opendocument import OpenDocumentText
from odf.text import P, H, List, ListItem
from odf.style import (
    Style, TextProperties, ParagraphProperties, TableColumnProperties,
    TableCellProperties, PageLayout, PageLayoutProperties, MasterPage
)
from odf.table import Table, TableColumn, TableRow, TableCell

def build_odt_documentation(output_paths):
    doc = OpenDocumentText()

    # --- DEFINE DOCUMENT STYLES ---
    # Page Layout (A4, 2cm margins)
    pl = PageLayout(name="StandardPageLayout")
    pl.addElement(PageLayoutProperties(
        pagewidth="21.0cm", pageheight="29.7cm",
        margintop="2.0cm", marginbottom="2.0cm",
        marginleft="2.0cm", marginright="2.0cm"
    ))
    doc.automaticstyles.addElement(pl)
    mp = MasterPage(name="Standard", pagelayoutname="StandardPageLayout")
    doc.masterstyles.addElement(mp)

    # Document Title Style
    style_title = Style(name="DocTitle", family="paragraph")
    style_title.addElement(ParagraphProperties(margintop="0.4cm", marginbottom="0.2cm", textalign="center"))
    style_title.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="24pt", fontweight="bold", color="#1e1b4b"))
    doc.styles.addElement(style_title)

    # Document Subtitle Style
    style_subtitle = Style(name="DocSubtitle", family="paragraph")
    style_subtitle.addElement(ParagraphProperties(marginbottom="0.6cm", textalign="center"))
    style_subtitle.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="12pt", fontstyle="italic", color="#4338ca"))
    doc.styles.addElement(style_subtitle)

    # Heading 1 Style
    style_h1 = Style(name="Heading 1", family="paragraph")
    style_h1.addElement(ParagraphProperties(margintop="0.8cm", marginbottom="0.3cm"))
    style_h1.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="16pt", fontweight="bold", color="#0f172a"))
    doc.styles.addElement(style_h1)

    # Heading 2 Style
    style_h2 = Style(name="Heading 2", family="paragraph")
    style_h2.addElement(ParagraphProperties(margintop="0.5cm", marginbottom="0.2cm"))
    style_h2.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="13pt", fontweight="bold", color="#1e293b"))
    doc.styles.addElement(style_h2)

    # Heading 3 Style
    style_h3 = Style(name="Heading 3", family="paragraph")
    style_h3.addElement(ParagraphProperties(margintop="0.3cm", marginbottom="0.1cm"))
    style_h3.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="11pt", fontweight="bold", color="#334155"))
    doc.styles.addElement(style_h3)

    # Body Text Style
    style_body = Style(name="StandardBody", family="paragraph")
    style_body.addElement(ParagraphProperties(marginbottom="0.25cm"))
    style_body.addElement(TextProperties(fontfamily="Liberation Serif", fontsize="10.5pt", color="#1e293b"))
    doc.styles.addElement(style_body)

    # Math / Formula Box Style
    style_mathbox = Style(name="MathBox", family="paragraph")
    style_mathbox.addElement(ParagraphProperties(
        margintop="0.2cm", marginbottom="0.25cm",
        backgroundcolor="#f8fafc", textalign="center"
    ))
    style_mathbox.addElement(TextProperties(fontfamily="Liberation Mono", fontsize="10pt", fontweight="bold", color="#0f172a"))
    doc.styles.addElement(style_mathbox)

    # Code Block Style
    style_code = Style(name="CodeBlock", family="paragraph")
    style_code.addElement(ParagraphProperties(
        margintop="0.2cm", marginbottom="0.25cm",
        backgroundcolor="#0f172a"
    ))
    style_code.addElement(TextProperties(fontfamily="Liberation Mono", fontsize="9pt", color="#38bdf8"))
    doc.styles.addElement(style_code)

    # Bullet List Item Style
    style_bullet = Style(name="BulletItem", family="paragraph")
    style_bullet.addElement(ParagraphProperties(marginleft="0.5cm", marginbottom="0.15cm"))
    style_bullet.addElement(TextProperties(fontfamily="Liberation Serif", fontsize="10.5pt", color="#334155"))
    doc.styles.addElement(style_bullet)

    # Table Header Style
    style_th = Style(name="TableHeader", family="table-cell")
    style_th.addElement(TableCellProperties(backgroundcolor="#1e1b4b"))
    doc.styles.addElement(style_th)

    style_th_text = Style(name="TableHeaderText", family="paragraph")
    style_th_text.addElement(ParagraphProperties(textalign="center"))
    style_th_text.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="9.5pt", fontweight="bold", color="#ffffff"))
    doc.styles.addElement(style_th_text)

    # Table Cell Style
    style_td = Style(name="TableCell", family="table-cell")
    style_td.addElement(TableCellProperties(backgroundcolor="#ffffff"))
    doc.styles.addElement(style_td)

    style_td_alt = Style(name="TableCellAlt", family="table-cell")
    style_td_alt.addElement(TableCellProperties(backgroundcolor="#f8fafc"))
    doc.styles.addElement(style_td_alt)

    style_td_text = Style(name="TableCellText", family="paragraph")
    style_td_text.addElement(TextProperties(fontfamily="Liberation Sans", fontsize="9pt", color="#1e293b"))
    doc.styles.addElement(style_td_text)


    # --- HELPER FUNCTIONS ---
    def add_p(text, style=style_body):
        doc.text.addElement(P(stylename=style, text=text))

    def add_h1(text):
        doc.text.addElement(H(outlinelevel=1, stylename=style_h1, text=text))

    def add_h2(text):
        doc.text.addElement(H(outlinelevel=2, stylename=style_h2, text=text))

    def add_h3(text):
        doc.text.addElement(H(outlinelevel=3, stylename=style_h3, text=text))

    def add_math(text):
        doc.text.addElement(P(stylename=style_mathbox, text=text))

    def add_code(text):
        doc.text.addElement(P(stylename=style_code, text=text))

    def add_bullet(text):
        doc.text.addElement(P(stylename=style_bullet, text=f"•  {text}"))


    # --- DOCUMENT HEADER & COVER ---
    add_p("QOaaS ENTERPRISE DOCUMENTATION", style_subtitle)
    doc.text.addElement(P(stylename=style_title, text="Enterprise Quantum Optimization-as-a-Service (QOaaS) Platform"))
    add_p("System Architecture, Engineering Specifications & Mathematical QUBO Formulations", style_subtitle)
    add_p("Document Version: 1.0.0 | Date: August 2026 | Author: QOaaS Core Engineering Team", style_subtitle)

    add_p("_________________________________________________________________________________")


    # --- SECTION 1: EXECUTIVE SUMMARY ---
    add_h1("1. Executive Summary & Value Proposition")
    add_p(
        "The Enterprise Quantum Optimization-as-a-Service (QOaaS) platform is a full-stack SaaS solution "
        "designed to democratize quantum computing for business users. Traditional combinatorial optimization problems "
        "in corporate environments—such as continuous portfolio mean-variance allocation in finance and multi-shift employee "
        "roster scheduling in operations—are NP-hard. As the number of decision variables N grows, classical brute-force "
        "and exact solvers scale exponentially with complexity O(2^N)."
    )
    add_p(
        "Quantum algorithms such as the Quantum Approximate Optimization Algorithm (QAOA) and Quantum Annealing offer "
        "potential polynomial speedups by reformulating constrained business objectives into Quadratic Unconstrained Binary "
        "Optimization (QUBO) energy landscapes. However, translating enterprise row data (CSV files, SQL databases) into "
        "symmetric QUBO coupling matrices Q and quantum gate circuits requires deep expertise in quantum mechanics, matrix algebra, "
        "and parameter tuning."
    )
    add_p(
        "QOaaS completely bridges this gap. Business users simply upload raw dataset CSV files via an intuitive web dashboard. "
        "The platform automatically executes mathematical variable synthesis, continuous-to-binary discretization, penalty "
        "parameter computation, QUBO matrix assembly, QAOA statevector simulation, and greedy constraint repair. Output solutions "
        "are delivered as validated allocation vectors, interactive analytical charts, executive PDF reports, and cryptographically "
        "verifiable Quantum Random Number Generator (QRNG) tokens."
    )


    # --- SECTION 2: ARCHITECTURE & MODULE BREAKDOWN ---
    add_h1("2. System Architecture & Technical Stack")
    add_p(
        "The platform is architected as a modern, decoupled micro-service system comprising a responsive Next.js frontend, "
        "an asynchronous FastAPI backend gateway, a high-performance Python scientific computing engine, and multi-solver routing."
    )

    add_h2("2.1 Technical Stack Overview")
    add_bullet("Frontend Layer: Next.js 15, React 19, TypeScript, TailwindCSS (glassmorphism UI), Recharts, Framer Motion, KaTeX.")
    add_bullet("API Gateway Layer: FastAPI, Uvicorn, Python 3.10+, Pydantic v2 schemas, CORS middleware, RESTful JSON interfaces.")
    add_bullet("Database & Persistence: SQLite (development) / PostgreSQL (production) with SQLAlchemy ORM schemas.")
    add_bullet("Core Scientific Stack: NumPy, SciPy (optimize & stats), Pandas, Qiskit / Qiskit Aer (quantum circuit simulation).")
    add_bullet("Reporting & Verification: ReportLab PDF generator, SMTP Mailer, ANU QRNG API integration.")

    add_h2("2.2 Internal Core Modules")
    add_bullet("Automatic Math Modeling (app/services/modeling.py): Analyzes input datasets, infers column schemas, calculates expected returns and covariance matrices for assets, and structures shift demand and wage matrices for employees.")
    add_bullet("QUBO Compiler Engine (app/services/qubo.py): Discretizes continuous variables into binary representations, formulates linear cost and quadratic coupling terms, and integrates penalty parameters for budget and coverage constraints.")
    add_bullet("Solver Selection Router (app/services/quantum.py): Directs small/medium QUBO matrices (N <= 12 qubits) to direct NumPy QAOA statevector simulation, and larger matrices to Simulated Annealing or Block-Decomposition Solvers.")
    add_bullet("Greedy Constraint Repair Engine (app/services/quantum.py): Performs post-processing normalization on raw quantum output bitstrings to guarantee 100% compliance with business constraints (e.g. sum w_i = 1.0, exact shift coverage).")
    add_bullet("AI Explanation Engine (app/services/ai.py): Translates complex optimization metrics (volatility, Sharpe ratio, coverage gap) into plain-language executive narrative summaries.")
    add_bullet("Executive PDF & Email Dispatch (app/services/reports.py & email.py): Compiles downloadable ReportLab PDF audit reports and dispatches automated email notifications.")


    # --- SECTION 3: CLEAR MATHEMATICAL QUBO FORMULATION ---
    add_h1("3. Mathematical QUBO Formulations (Core Specifications)")
    add_p(
        "This section provides rigorous mathematical derivations and exact software implementation details for the "
        "Quadratic Unconstrained Binary Optimization (QUBO) formulations across both the Finance and Operations business domains."
    )

    add_h2("3.1 Foundations of QUBO")
    add_p(
        "Quantum processors and annealing systems solve unconstrained minimization problems over binary decision vectors x in {0, 1}^N. "
        "The QUBO cost function is defined as:"
    )
    add_math("E(x) = x^T Q x = sum_{i=1}^N Q_{ii} x_i + sum_{1 <= i < j <= N} (Q_{ij} + Q_{ji}) x_i x_j,   x_i in {0, 1}")
    add_p(
        "where Q is an N x N real symmetric matrix. Because x_i in {0,1}, x_i^2 = x_i. Therefore, diagonal elements Q_{ii} "
        "represent the linear cost/return terms, while off-diagonal elements Q_{ij} represent quadratic interactions or penalty couplings. "
        "Equality and inequality constraints g(x) = c are incorporated using the Quadratic Penalty Method:"
    )
    add_math("Penalty Term = P * ( g(x) - c )^2")
    add_p("where P > 0 is a large scalar penalty constant chosen to dominate objective trade-offs when constraints are violated.")


    add_h2("3.2 Finance Domain: Portfolio Optimization Formulation")
    add_p(
        "In modern Markowitz Mean-Variance Portfolio Optimization, the goal is to allocate capital weights w_i in [0, 1] across M assets "
        "to minimize risk volatility while achieving target expected returns, subject to a total budget constraint sum_{i=1}^M w_i = 1."
    )

    add_h3("Variable Discretization")
    add_p(
        "Because quantum computers operate on binary qubits x_{i,k} in {0,1}, each continuous weight w_i is approximated using B binary bits:"
    )
    add_math("w_i ≈ sum_{k=0}^{B-1} 2^{-(k+1)} * x_{i,k} = 0.5 * x_{i,0} + 0.25 * x_{i,1} + 0.125 * x_{i,2}  (for B = 3)")
    add_p(
        "For M assets and B bits per asset, the total number of binary decision variables (qubits) is N = M * B. "
        "For example, a 6-asset portfolio with 3-bit discretization requires N = 6 * 3 = 18 qubits."
    )

    add_h3("Markowitz Objective Function")
    add_p("The classical objective function minimizes risk covariance minus risk-aversion scaled return:")
    add_math("Objective = sum_{i=1}^M sum_{j=1}^M w_i w_j Cov(i,j) - lambda * sum_{i=1}^M w_i R_i")
    add_p("Substituting the binary weight expansions into the objective yields:")
    add_math("Risk Term = sum_{i,j=1}^M sum_{k,m=0}^{B-1} 2^{-(k+1)} * 2^{-(m+1)} * Cov(i,j) * x_{i,k} * x_{j,m}")
    add_math("Return Term = - lambda * sum_{i=1}^M sum_{k=0}^{B-1} 2^{-(k+1)} * R_i * x_{i,k}")

    add_h3("Portfolio Budget Penalty Constraint")
    add_p("The budget constraint sum_{i=1}^M w_i = 1 is incorporated as a squared penalty with scalar constant P:")
    add_math("Penalty = P * ( sum_{i=1}^M sum_{k=0}^{B-1} 2^{-(k+1)} * x_{i,k} - 1 )^2")
    add_p("Expanding the squared summation yields:")
    add_math("Penalty = P * [ sum_{i,k} sum_{j,m} 2^{-(k+1)} * 2^{-(m+1)} * x_{i,k} * x_{j,m} - 2 * sum_{i,k} 2^{-(k+1)} * x_{i,k} + 1 ]")

    add_h3("Complete Combined QUBO Matrix Elements")
    add_p("Combining the objective terms and expanded penalty terms gives the exact QUBO matrix coefficients:")
    add_bullet("Diagonal Elements Q_{(i,k),(i,k)} (Linear Terms):")
    add_math("Q_{(i,k),(i,k)} = 2^{-2(k+1)} * Cov(i,i) - lambda * 2^{-(k+1)} * R_i - 2 * P * 2^{-(k+1)} + P * 2^{-2(k+1)}")
    add_bullet("Off-Diagonal Elements Q_{(i,k),(j,m)} (Quadratic Interaction Terms for (i,k) != (j,m)):")
    add_math("Q_{(i,k),(j,m)} = 2^{-(k+1)} * 2^{-(m+1)} * Cov(i,j) + P * 2^{-(k+1)} * 2^{-(m+1)}")
    add_p("Penalty Factor Scale: P = 2.5 * max(R_i) (dynamically computed in app/services/qubo.py).")


    add_h2("3.3 Operations Domain: Staffing & Shift Roster Optimization Formulation")
    add_p(
        "In employee scheduling, the platform assigns E employees across S shifts to minimize labor wage costs while strictly satisfying "
        "shift headcount demand, preventing employee shift overlap, and obeying employee availability constraints."
    )

    add_h3("Decision Variables")
    add_p(
        "The decision variables are natively binary: x_{e,s} in {0, 1}, where x_{e,s} = 1 if employee e is assigned to shift s, "
        "and x_{e,s} = 0 otherwise. Total variables N = E * S."
    )

    add_h3("Objective Function")
    add_p("Minimize total daily labor cost based on hourly wage C_e and shift length (8 hours):")
    add_math("Min Objective = sum_{e=1}^E sum_{s=1}^S C_{e,s} * x_{e,s}")

    add_h3("Constraint Penalties")
    add_bullet("1. Shift Demand Constraint: For each shift s with required demand D_s, penalty P_demand = 200.0:")
    add_math("Penalty_demand = P_demand * sum_{s=1}^S ( sum_{e=1}^E x_{e,s} - D_s )^2")
    add_math("= P_demand * sum_{s=1}^S [ sum_{e1, e2} x_{e1,s} * x_{e2,s} - 2 * D_s * sum_{e} x_{e,s} + D_s^2 ]")

    add_bullet("2. Maximum Shift Overlap Constraint: At most 1 shift per employee per day, penalty P_max = 300.0:")
    add_math("Penalty_max = P_max * sum_{e=1}^E sum_{1 <= s1 < s2 <= S} x_{e,s1} * x_{e,s2}")

    add_bullet("3. Employee Unavailability Constraint: Heavy diagonal penalty for unassigned shifts, P_avail = 500.0:")
    add_math("Penalty_avail = P_avail * sum_{(e,s) not in Availability} x_{e,s}")

    add_h3("Combined Staffing QUBO Matrix Construction")
    add_bullet("Diagonal Element Q_{(e,s),(e,s)} = C_{e,s} + (P_avail if not available else 0) - 2 * D_s * P_demand + P_demand")
    add_bullet("Off-Diagonal Element Q_{(e1,s),(e2,s)} (Same shift s, different employees e1 != e2) = P_demand")
    add_bullet("Off-Diagonal Element Q_{(e,s1),(e,s2)} (Same employee e, different shifts s1 != s2) = P_max")


    # --- SECTION 4: QAOA QUANTUM CIRCUIT SIMULATION ---
    add_h1("4. QAOA Quantum Circuit Execution Engine")
    add_p(
        "To solve QUBO matrices on gate-based quantum processors, QOaaS maps the binary QUBO problem into a Cost Hamiltonian H_C "
        "and executes the Quantum Approximate Optimization Algorithm (QAOA)."
    )

    add_h2("4.1 Mapping QUBO to Pauli Z Cost Hamiltonian")
    add_p("Binary variables x_i in {0,1} are mapped to Pauli Z eigenvalues in {+1, -1} via the transformation x_i |-> (I - Z_i) / 2:")
    add_math("H_C = sum_{i=1}^N h_i Z_i + sum_{1 <= i < j <= N} J_{ij} Z_i Z_j")
    add_p("where local fields h_i and coupling coefficients J_{ij} are derived directly from QUBO matrix Q.")

    add_h2("4.2 QAOA Circuit Layer Sequence (p=1)")
    add_bullet("1. State Initialization: Apply Hadamard (H) gates to all N qubits to create uniform superposition |psi_0> = |+>^tensor N.")
    add_bullet("2. Cost Phase Layer U_C(gamma): Evolve under cost Hamiltonian for time gamma: U_C(gamma) = exp(-i * gamma * H_C). Implemented via Rz(2*gamma*h_i) gates and CNOT -> Rz(2*gamma*J_ij) -> CNOT gate pairs.")
    add_bullet("3. Mixer Rotation Layer U_M(beta): Evolve under transverse field mixer Hamiltonian H_M = sum_i X_i for time beta: U_M(beta) = exp(-i * beta * H_M) = prod_i Rx(2*beta).")
    add_bullet("4. Measurement & Sampling: Sample final statevector |psi(gamma, beta)> in computational Z-basis.")

    add_h2("4.3 NumPy Statevector Engine Implementation (app/services/quantum.py)")
    add_code(
"""def numpy_qaoa_solve(Q: np.ndarray, p: int = 1) -> Tuple[np.ndarray, float]:
    n = Q.shape[0]
    num_states = 2 ** n
    energies = np.array([b.T @ Q @ b for b in all_bitstrings])
    
    state = np.ones(num_states) / np.sqrt(num_states)
    for gamma in np.linspace(0, np.pi, 6):
        state_cost = state * np.exp(-1j * gamma * energies)
        for beta in np.linspace(0, np.pi, 6):
            # Apply Rx(2*beta) tensor product array operations
            probabilities = np.abs(state_mixer) ** 2
            expected_energy = np.sum(probabilities * energies)
    return best_bitstring, best_energy"""
    )


    # --- SECTION 5: CONSTRAINT REPAIR ENGINE ---
    add_h1("5. Post-Processing & Greedy Constraint Repair")
    add_p(
        "Quantum measurement sampling yields probabilistic bitstrings. To guarantee 100% business compliance, QOaaS runs deterministic "
        "greedy repair post-processors:"
    )
    add_h2("5.1 Portfolio Weight Normalization")
    add_p("Raw binary weights w_i = sum_k 2^{-(k+1)} x_{i,k} are normalized to sum strictly to 1.0:")
    add_math("Normalized Weight w_i_final = w_i / sum_{j=1}^M w_j")

    add_h2("5.2 Staffing Roster Coverage Repair")
    add_p(
        "If a shift s has a coverage deficit (sum_e x_{e,s} < D_s), the repair engine greedily assigns available employees with the lowest "
        "hourly wage until demand D_s is fully satisfied."
    )


    # --- SECTION 6: API REFERENCE & ENDPOINTS ---
    add_h1("6. REST API Interface Specification")
    add_p("FastAPI Gateway exposes endpoints under /api/v1 for authentication, optimization submission, and job queries.")

    # Table of APIs
    table = Table()
    table.addElement(TableColumn(numbercolumnsrepeated=1))
    table.addElement(TableColumn(numbercolumnsrepeated=1))
    table.addElement(TableColumn(numbercolumnsrepeated=1))

    # Header Row
    tr_h = TableRow()
    cell_1 = TableCell(stylename=style_th); cell_1.addElement(P(stylename=style_th_text, text="HTTP Method & Endpoint"))
    cell_2 = TableCell(stylename=style_th); cell_2.addElement(P(stylename=style_th_text, text="Description"))
    cell_3 = TableCell(stylename=style_th); cell_3.addElement(P(stylename=style_th_text, text="Payload / Parameters"))
    tr_h.addElement(cell_1); tr_h.addElement(cell_2); tr_h.addElement(cell_3)
    table.addElement(tr_h)

    endpoints = [
        ("POST /api/v1/jobs/submit", "Submits CSV dataset for automatic modeling & QUBO execution", "Multipart file upload + domain_type"),
        ("GET /api/v1/jobs/{job_id}", "Retrieves optimization execution status, QUBO metrics & vectors", "Job ID path parameter"),
        ("GET /api/v1/jobs/{job_id}/qrng", "Generates ANU physical quantum entropy verification token", "Job ID path parameter"),
        ("GET /api/v1/jobs/{job_id}/report", "Generates and downloads ReportLab executive PDF report", "Job ID path parameter"),
        ("POST /api/v1/jobs/{job_id}/email", "Dispatches executive PDF report via SMTP mailer", "Recipient email address JSON")
    ]

    for idx, (ep, desc, payload) in enumerate(endpoints):
        tr = TableRow()
        c_style = style_td_alt if idx % 2 == 1 else style_td
        c1 = TableCell(stylename=c_style); c1.addElement(P(stylename=style_td_text, text=ep))
        c2 = TableCell(stylename=c_style); c2.addElement(P(stylename=style_td_text, text=desc))
        c3 = TableCell(stylename=c_style); c3.addElement(P(stylename=style_td_text, text=payload))
        tr.addElement(c1); tr.addElement(c2); tr.addElement(c3)
        table.addElement(tr)

    doc.text.addElement(table)


    # --- SECTION 7: DEPLOYMENT & SUMMARY ---
    add_h1("7. Deployment & Operational Verification")
    add_p("QOaaS is containerized using Docker Compose for simple production deployment:")
    add_code(
"""# Run full platform via Docker Compose
docker compose up --build

# Backend URL: http://localhost:8000
# Frontend URL: http://localhost:3000
# Swagger API Docs: http://localhost:8000/docs"""
    )
    add_p(
        "Verification unit tests are located in backend/test_phase1.py through backend/test_pipeline.py and can be executed via pytest."
    )

    # Save to output paths
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Successfully generated documentation ODT file at: {path}")

if __name__ == "__main__":
    paths = [
        "/home/rgukt/.gemini/antigravity/scratch/qoaas-platform/QOaaS_Platform_Documentation.odt",
        "/home/rgukt/.gemini/antigravity/brain/587f4738-1825-4a3c-803c-d9116b92ab3e/QOaaS_Platform_Documentation.odt"
    ]
    build_odt_documentation(paths)
