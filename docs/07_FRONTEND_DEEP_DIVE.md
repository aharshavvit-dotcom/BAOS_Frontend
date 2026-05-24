# FRONTEND DEEP DIVE — Next.js 16 + React 19 + TypeScript

> Complete code-level documentation of the BAOS AI frontend architecture

---

# 1. TECHNOLOGY STACK & RATIONALE

| Technology | Version | Role | Why This Choice |
|---|---|---|---|
| **Next.js** | 16.2.1 | Meta-framework | App Router, SSR, file-based routing, optimized builds |
| **React** | 19.2.4 | UI library | Latest concurrent features, Suspense, use() hook |
| **TypeScript** | 5.x | Type safety | Catches 50+ interface mismatches at compile time |
| **Tailwind CSS** | 4.x | Styling | `@theme inline` token system, utility-first, no CSS-in-JS runtime |
| **Zustand** | 5.0.12 | State management | 3 stores, no Redux boilerplate, hook-native |
| **Recharts** | 3.8.1 | Charts | React-native, responsive, composable chart components |
| **Axios** | 1.14.0 | HTTP client | Interceptors for JWT refresh, request/response transforms |
| **Socket.IO Client** | 4.8.3 | WebSocket | Auto-reconnect, transport fallback, room subscription |
| **Framer Motion** | 12.38.0 | Animations | Declarative, layout-aware animations |

---

# 2. DIRECTORY STRUCTURE (Code-Level)

```
frontend-next/
├── package.json                    # Dependencies + scripts (dev, build, start, lint)
├── tsconfig.json                   # TypeScript config with @/ path alias
├── next.config.ts                  # Next.js configuration
├── postcss.config.mjs              # PostCSS for Tailwind v4
│
└── src/
    ├── app/                        # ─── Next.js App Router (file-based routing) ───
    │   ├── layout.tsx              # Root layout — HTML skeleton, font imports, metadata
    │   ├── page.tsx                # Landing page (/) — 436 lines, hero + charts + CTA
    │   ├── globals.css             # Design system — 663 lines, all CSS tokens + components
    │   ├── login/page.tsx          # Login page (/login)
    │   ├── signup/page.tsx         # Signup page (/signup)
    │   └── dashboard/
    │       ├── layout.tsx          # Dashboard layout — sidebar + topbar (persistent)
    │       ├── page.tsx            # Dashboard overview (/dashboard) — KPIs + charts
    │       ├── optimizer/
    │       │   ├── page.tsx        # Multi-vessel optimizer (/dashboard/optimizer)
    │       │   └── types.ts        # Optimizer-specific types
    │       ├── recommend/page.tsx  # AI recommendation (/dashboard/recommend)
    │       ├── commercial/         # Commercial intelligence pages
    │       ├── analytics/          # Analytics pages
    │       └── alerts/             # Alert management
    │
    ├── store/                      # ─── Zustand State Management ───
    │   ├── authStore.ts            # Auth state — login/logout/demo mode (169 lines)
    │   ├── dashboardStore.ts       # KPIs, charts, recommendations (93 lines)
    │   └── uiStore.ts              # Toast notifications, UI toggles (43 lines)
    │
    ├── hooks/                      # ─── Custom React Hooks ───
    │   ├── useSocket.ts            # WebSocket lifecycle — connect/disconnect/events (62 lines)
    │   └── useAnimatedCounter.ts   # Animated number counter with easeOutCubic (51 lines)
    │
    ├── lib/                        # ─── Infrastructure Utilities ───
    │   ├── api.ts                  # Axios instance with JWT interceptors (61 lines)
    │   └── socket.ts              # Socket.IO singleton client (42 lines)
    │
    └── types/                      # ─── TypeScript Interfaces ───
        └── index.ts                # All shared types — 173 lines, 15+ interfaces
```

---

# 3. DESIGN SYSTEM (`globals.css` — 663 lines)

The design system implements a comprehensive **CSS custom property** architecture using Tailwind v4's `@theme inline` directive.

## 3.1 Color Palette

```css
@theme inline {
  --color-primary:        #0066CC;     /* Maritime blue */
  --color-primary-light:  #3388DD;     /* Hover state */
  --color-primary-dark:   #004C99;     /* Active state */
  --color-success:        #10B981;     /* Green — SLA compliance, positive KPI */
  --color-warning:        #F59E0B;     /* Amber — medium risk, warnings */
  --color-danger:         #EF4444;     /* Red — violations, high risk */
  --color-info:           #3B82F6;     /* Blue — informational */

  --color-dark:           #FFFFFF;     /* Background */
  --color-dark-card:      #F8FAFC;     /* Card backgrounds */
  --color-dark-surface:   #F1F5F9;     /* Elevated surfaces */
  --color-dark-border:    #E2E8F0;     /* Borders and dividers */

  --color-text-primary:   #0F172A;     /* Main text */
  --color-text-secondary: #334155;     /* Secondary text */
  --color-text-muted:     #64748B;     /* Labels, hints */
  --color-text-accent:    #94A3B8;     /* Disabled, placeholder */
}
```

## 3.2 Typography

```css
--font-display: 'Montserrat', sans-serif;   /* Headings, buttons, labels */
--font-body: 'Open Sans', sans-serif;       /* Body text, paragraphs */
--font-code: 'Fira Mono', monospace;        /* Code blocks, data values */
```

## 3.3 Component Classes

| Class | Purpose | Key Properties |
|---|---|---|
| `.btn` | Base button | `font-display`, 600 weight, `radius-md`, `0.2s` transition |
| `.btn-primary` | Primary CTA | `--color-primary` bg, white text, hover lift + shadow |
| `.btn-secondary` | Secondary action | `--color-dark-surface` bg, bordered |
| `.btn-ghost` | Minimal button | Transparent bg, hover fills 5% black |
| `.btn-outline` | Outlined CTA | Border-only, fills on hover |
| `.btn-sm` / `.btn-lg` | Size variants | 8px/16px padding |
| `.card` | Interactive card | `--color-dark-card` bg, bordered, hover lift + shadow |
| `.card-flat` | Static card | Same as card without hover effect |
| `.form-input` | Text input | Full-width, `--color-dark` bg, focus ring `--color-primary` |
| `.badge` | Status pill | Rounded, 11px uppercase, color-coded |
| `.sidebar-link` | Nav link | Icon gap, `--radius-md`, active state with primary bg |
| `.rec-tab` | Tab button | Pill-shaped, active = primary fill |
| `.glass` | Glassmorphism | `backdrop-filter: blur(12px)`, semi-transparent bg |
| `.heatmap-cell` | Heatmap grid cell | Color-coded bg, hover scale, numeric display |

## 3.4 Animations

| Animation | Trigger | Effect |
|---|---|---|
| `fadeInUp` | Page mount | Opacity 0→1, translateY 30→0 |
| `fadeIn` | Component mount | Opacity 0→1 |
| `slideInLeft` | Sidebar mount | Opacity 0→1, translateX -30→0 |
| `slideInRight` | Toast notification | Opacity 0→1, translateX 100%→0 |
| `pulse-glow` | Active element | Box-shadow pulsing with primary color |
| Scroll reveal | IntersectionObserver | `.reveal` → `.reveal.visible` transition |

---

# 4. STATE MANAGEMENT (Zustand)

## 4.1 Auth Store (`authStore.ts` — 169 lines)

```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}
```

**Key Architecture Decisions:**

1. **Dual-mode authentication:** The store first attempts a real backend login (`POST /api/auth/login`). If the backend is unreachable (network error), it falls back to **demo mode** with client-side credential validation.

2. **Demo user registry:** Two hardcoded demo accounts (`admin@baos.ai`, `operator@baos.ai`) provide instant access without infrastructure. Any email/password combo with ≥4 character password also works in demo mode.

3. **Token persistence:** JWT tokens stored in `localStorage` under `baos_access_token` and `baos_refresh_token`. Demo tokens prefixed with `demo_` for differentiation.

4. **Session restoration:** `checkAuth()` detects `demo_` prefix and restores user from `localStorage` JSON snapshot rather than hitting `/api/auth/me`.

## 4.2 Dashboard Store (`dashboardStore.ts` — 93 lines)

```typescript
interface DashboardState {
  kpis: KPIData | null;
  charts: ChartsData | null;
  recommendations: DashboardRecommendation[];
  loading: boolean;
  lastUpdated: string | null;
  fetchKPIs: (portCode?: string) => Promise<void>;
  fetchCharts: (portCode?: string, timeRange?: string) => Promise<void>;
  fetchRecommendations: (portCode?: string, status?: string) => Promise<void>;
  updateKPIs: (kpis: KPIData) => void;          // Called by WebSocket
  addRecommendation: (rec: DashboardRecommendation) => void;
}
```

**Key Architecture Decisions:**

1. **Silent fallback:** Every `fetch*` method wraps API calls in try/catch with `AbortSignal.timeout(3000)`. On failure, static fallback data populates the dashboard — no error modals, no broken state.

2. **Real-time updates:** `updateKPIs()` and `addRecommendation()` are called directly by the `useSocket` hook when WebSocket events arrive, enabling push-based updates without polling.

## 4.3 UI Store (`uiStore.ts`)

Manages global UI state: toast notifications, sidebar collapse, loading overlays. Provides `showToast(message, type)` consumed by the WebSocket hook for server-push notifications.

---

# 5. API CLIENT (`lib/api.ts` — 61 lines)

```typescript
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});
```

### Request Interceptor
Automatically attaches JWT from `localStorage`:
```typescript
config.headers.Authorization = `Bearer ${token}`;
```

### Response Interceptor (401 Handling)
Implements **silent token refresh**:
1. On 401 response → check if retry already attempted (`_retry` flag)
2. Read `refresh_token` from localStorage
3. POST to `/api/auth/refresh` → get new `access_token`
4. Retry the original request with new token
5. On refresh failure → clear tokens → redirect to `/login`

**Design Decision:** The `_retry` flag prevents infinite refresh loops. Only one refresh attempt per failed request.

---

# 6. WEBSOCKET INTEGRATION

## 6.1 Socket Client (`lib/socket.ts` — 42 lines)

```typescript
socket = io(SOCKET_URL, {
  path: '/ws/socket.io',
  transports: ['websocket', 'polling'],    // Prefer WS, fallback to HTTP polling
  autoConnect: false,                       // Manual connect via hook
  reconnectionAttempts: 3,                  // Limited retries (no spam)
  reconnectionDelay: 5000,                  // 5s between retries
  timeout: 5000,                            // Connection timeout
  auth: () => ({                            // Dynamic JWT from localStorage
    token: localStorage.getItem('baos_access_token')
  }),
});
```

**Singleton pattern:** Only one Socket.IO instance exists per page lifecycle. `getSocket()` returns the cached instance.

## 6.2 Socket Hook (`hooks/useSocket.ts` — 62 lines)

```typescript
export function useSocket() {
  // Prevents double-connection in React StrictMode
  const connected = useRef(false);

  useEffect(() => {
    if (connected.current) return;
    connected.current = true;

    const socket = getSocket();
    socket.on('kpi_update', (data) => updateKPIs(data));
    socket.on('new_assignment', (data) => {
      addRecommendation(data);
      showToast(`New assignment: ${data.vessel_name} → ${data.berth_name}`, 'info');
    });
    socket.on('notification', (data) => showToast(data.message, data.type));
    connectSocket();

    return () => { disconnectSocket(); connected.current = false; };
  }, []);
}
```

**Key Design Decisions:**
- `useRef` guard prevents double-connection in React 18+ StrictMode (which mounts effects twice in dev)
- Cleanup properly disconnects on unmount
- WebSocket is only connected from the Dashboard layout — not the landing/login pages

---

# 7. TYPESCRIPT TYPE SYSTEM (`types/index.ts` — 173 lines)

### Core Domain Types

```typescript
// Authentication
interface User { id, email, full_name, company, port_code, port_name, role }
interface AuthTokens { access_token, refresh_token, token_type }
interface LoginCredentials { email, password }
interface SignupData { email, password, full_name, company, port_code }

// Dashboard
interface KPIData { vessels_count, revenue, cost, utilization_pct, sla_compliance_pct, avg_turnaround_hours, kpi_cards: KPIValue[] }
interface ChartsData { monthly_comparison, utilization_trend, vessel_distribution, cost_breakdown }
interface ChartDataset { label, data[], backgroundColor, borderColor, fill, tension, borderRadius, ... }

// Recommendations
interface BerthRecommendation { berth_code, berth_name, confidence, technical_score, commercial_score, reasoning, expected_turnaround_hours }
interface RecommendationRequest { vessel_name, vessel_type, loa_m, beam_m, draft_m, dwt, cargo_type, cargo_tons, eta, port_code }
interface DashboardRecommendation { id, vessel_name, vessel_type, berth_name, confidence, status, created_at }

// Domain
interface Vessel { id, name, vessel_type, loa_m, beam_m, draft_m, dwt, cargo_type, cargo_tons, imo_number, company }
interface Port { id, name, code, country }
interface Berth { id, port_id, code, name, max_loa_m, max_beam_m, max_draft_m, depth_m, is_available }

// UI
interface Toast { id, message, type: 'success' | 'error' | 'info' | 'warning' }
type FilterStatus = 'all' | 'pending' | 'accepted' | 'rejected'
```

**Design Decision:** All types are co-located in `types/index.ts` rather than per-component because the same interfaces (`Vessel`, `Berth`, `KPIData`) are consumed by multiple stores, hooks, and page components. This eliminates circular import risks.

---

# 8. PAGE COMPONENTS

## 8.1 Landing Page (`app/page.tsx` — 436 lines)

**Sections:**
1. **Navbar** — Fixed, glassmorphism on scroll (`navScrolled` state), links to Login/Signup
2. **Hero** — Gradient background, animated counters (IntersectionObserver + requestAnimationFrame), CTA buttons
3. **Features** — 6-card grid with scroll reveal (staggered delay: `i * 100ms`)
4. **KPI Metrics** — 4 animated counter cards (vessels, turnaround, utilization, revenue)
5. **Charts** — 4 Recharts charts: berth utilization bar, turnaround trend area, revenue bar, vessel type pie
6. **Heatmap** — Custom CSS grid (7 days × 5 berths) with color-coded utilization cells
7. **CTA** — Final call-to-action section
8. **Footer** — Copyright notice

**Custom Components Built Inline:**
- `AnimatedCounter` — IntersectionObserver + requestAnimationFrame + easeOutCubic easing
- `Reveal` — IntersectionObserver scroll-trigger with configurable delay
- `getHeatmapColor()` — Maps utilization % → red/amber/green color tuple

## 8.2 Dashboard Layout (`app/dashboard/layout.tsx`)

**Architecture:** Persistent sidebar + topbar wrapper that all dashboard pages share.
- **Sidebar:** Navigation links (Dashboard, Optimizer, Recommend, Commercial, Analytics, Alerts) with active state detection via `usePathname()`
- **Topbar:** Page title, user avatar, profile dropdown with logout
- **WebSocket:** `useSocket()` hook called at layout level — ensures single connection for all dashboard pages

## 8.3 Dashboard Overview (`app/dashboard/page.tsx`)

**Architecture:** 4 KPI cards + 4 Recharts + recent recommendations table
- Fetches from `dashboardStore.fetchKPIs()` on mount
- Animated counters for each KPI value
- Responsive grid: 4-col on desktop, 2-col on tablet, 1-col on mobile

## 8.4 Optimizer Page (`app/dashboard/optimizer/page.tsx`)

**The most complex page in the application.** Implements:
- Multi-step form: vessel configuration → lever tuning → results
- Dynamic vessel list with add/remove
- 10+ optimization weight sliders with per-ship-type overrides
- Client-side feasibility checking (when backend unavailable)
- Interactive Gantt timeline with hover tooltips
- Feasibility matrix (vessel × berth) with 6-factor tooltip cards
- Schedule assignments table with "Change Berth" dropdown
- Cost breakdown table with "Change Berth" option
- AI explanation panels per assignment
- Calibrated confidence display
- Undo/redo for manual overrides

## 8.5 Recommendation Page (`app/dashboard/recommend/page.tsx`)

**Architecture:**
- Vessel input form (LOA, beam, draft, DWT, vessel type dropdown, cargo type dropdown)
- Submits to `POST /api/recommendations/get-recommendation`
- Displays top-3 berth recommendations with confidence bars
- Each recommendation has: pros/cons list, equipment match, throughput estimate
- Expandable "DECISION ANALYSIS" section with structured 4-category reasoning
- Berth allocation timeline showing expected wait + service time

---

# 9. DATA FLOW: FRONTEND → BACKEND → FRONTEND

```
┌──────────────────────────┐
│ React Component          │
│ (e.g., Optimizer Page)   │
└──────────┬───────────────┘
           │ User action (submit form, change berth, adjust lever)
           ▼
┌──────────────────────────┐
│ Zustand Store            │ Optimistic state update
│ (optimizerStore)         │
└──────────┬───────────────┘
           │ api.post('/api/v1/optimize', payload)
           ▼
┌──────────────────────────┐
│ Axios Instance           │ Attaches JWT token
│ (lib/api.ts)             │ 30s timeout
└──────────┬───────────────┘
           │ HTTP POST (JSON)
           ▼
┌──────────────────────────┐
│ FastAPI Backend           │
│ Route → Service → Engine │
└──────────┬───────────────┘
           │ JSON response (assignments, KPIs, costs, explanations)
           ▼
┌──────────────────────────┐
│ Axios Response           │ (or 401 → refresh → retry)
└──────────┬───────────────┘
           │ Store update with server response
           ▼
┌──────────────────────────┐
│ React Re-render          │ All subscribed components update:
│                          │ - Timeline visualization
│                          │ - Feasibility matrix
│                          │ - Cost breakdown table
│                          │ - Confidence panel
│                          │ - AI explanation panels
└──────────────────────────┘
```

**Parallel WebSocket Channel:**
```
Backend event (schedule_updated, kpi_refresh)
    │
    ▼
Socket.IO server (backend/routes/websocket.py)
    │ sio.emit('kpi_updated', data, room='kpi:INMAA')
    ▼
Socket.IO client (lib/socket.ts)
    │
    ▼
useSocket hook (hooks/useSocket.ts)
    │
    ▼
dashboardStore.updateKPIs(data) → React re-render
```
