{
  "design_system_name": "OmniTour SaaS (Hotels + Restaurants) — Dark Pro",
  "brand_attributes": [
    "professional + data-dense (Intercom/Zendesk cadence)",
    "calm under pressure (night-shift friendly)",
    "premium hospitality (guest-facing QR flows feel branded, not 'admin')",
    "trustworthy + precise (SLA, status, audit trails)",
    "fast-scannable (lists, boards, inbox tri-pane)"
  ],
  "audience_and_key_jobs": {
    "admin": ["configure tenant", "manage users/roles", "feature flags", "catalog (rooms/tables/menu)", "loyalty rules"],
    "staff": ["triage guest requests", "manage kitchen orders", "filter by department", "quick status changes"],
    "agent": ["respond to chats", "use AI suggestions", "find context fast"],
    "guest_qr": ["submit request", "track status", "order food", "call waiter", "pay/request bill", "join loyalty"]
  },

  "global_layout_principles": {
    "admin_staff_shell": {
      "pattern": "Tri-pane with resizable rails (Inbox-inspired)",
      "desktop_grid": "Left nav rail (72px icons) + secondary sidebar (320px list/filters) + main content (flex) + optional right inspector (360px)",
      "mobile": "Single column + bottom sheet for filters/inspector; keep primary action sticky",
      "notes": [
        "Use shadcn `Resizable` for list/main/inspector panes where relevant (inbox, CRM contact inspector).",
        "Keep topbar minimal: global search (⌘K), tenant switcher, notifications, profile."
      ]
    },
    "guest_shell": {
      "pattern": "Premium single-column, card-forward, thumb-reachable",
      "max_width": "max-w-md (guests) with full-bleed header image band",
      "sticky_elements": ["sticky bottom cart bar (restaurant)", "sticky status chip + last update (requests)"]
    }
  },

  "typography": {
    "font_pairing": {
      "display": {
        "family": "Space Grotesk",
        "use": "Dashboard headings, section titles, KPI numbers"
      },
      "body": {
        "family": "Inter",
        "use": "Dense UI, tables, forms, chat content"
      },
      "mono_optional": {
        "family": "IBM Plex Mono",
        "use": "IDs, QR codes, API keys, ledger references"
      }
    },
    "how_to_apply_in_react": {
      "google_fonts": [
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap",
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap"
      ],
      "tailwind_usage": {
        "heading_class": "font-[Space_Grotesk] tracking-[-0.02em]",
        "body_class": "font-[Inter]",
        "mono_class": "font-[IBM_Plex_Mono]"
      }
    },
    "size_hierarchy": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold",
      "h2": "text-base md:text-lg text-muted-foreground",
      "section_title": "text-lg font-semibold",
      "kpi_number": "text-2xl sm:text-3xl font-semibold",
      "body": "text-sm sm:text-base",
      "small": "text-xs text-muted-foreground"
    }
  },

  "color_system": {
    "mode": "dark-only",
    "tokens_css_custom_properties": {
      "instructions": "Replace current shadcn tokens in /frontend/src/index.css :root + .dark. Keep only dark usage; set html/body to .dark by default in app bootstrap.",
      "css": ":root{\n  --background: 222 47% 6%;\n  --foreground: 210 40% 98%;\n\n  --card: 222 44% 8%;\n  --card-foreground: 210 40% 98%;\n\n  --popover: 222 44% 8%;\n  --popover-foreground: 210 40% 98%;\n\n  --primary: 220 86% 60%; /* Indigo/Blue */\n  --primary-foreground: 222 47% 8%;\n\n  --secondary: 222 22% 14%;\n  --secondary-foreground: 210 40% 98%;\n\n  --muted: 222 18% 14%;\n  --muted-foreground: 215 16% 70%;\n\n  --accent: 221 30% 16%;\n  --accent-foreground: 210 40% 98%;\n\n  --destructive: 346 78% 56%; /* Rose */\n  --destructive-foreground: 210 40% 98%;\n\n  --border: 222 16% 18%;\n  --input: 222 16% 18%;\n  --ring: 220 86% 60%;\n\n  --success: 153 60% 45%; /* Emerald */\n  --warning: 38 92% 55%; /* Amber */\n  --info: 205 90% 55%;\n\n  --radius: 0.75rem;\n}\n\n.dark{\n  /* same as :root (dark-only) */\n}\n"
    },
    "semantic_usage": {
      "backgrounds": {
        "app_bg": "hsl(var(--background))",
        "surface_1": "hsl(var(--card))",
        "surface_2": "hsl(var(--secondary))",
        "surface_raised": "use shadow + border instead of brighter fill"
      },
      "text": {
        "primary": "hsl(var(--foreground))",
        "muted": "hsl(var(--muted-foreground))",
        "danger": "hsl(var(--destructive))",
        "success": "hsl(var(--success))"
      },
      "status_chips": {
        "open": "bg-[hsl(var(--info)/0.12)] text-[hsl(var(--info))] border-[hsl(var(--info)/0.25)]",
        "in_progress": "bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.25)]",
        "done": "bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.25)]",
        "warning": "bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.25)]",
        "error": "bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)/0.25)]"
      }
    },
    "gradients_and_texture": {
      "rule": "Use gradients only as large decorative backplates behind hero headers in guest panels or login (<=20% viewport).",
      "allowed_gradients": [
        "Login/Guest header: bg-[radial-gradient(60%_60%_at_20%_0%,hsl(220_86%_60%/0.20)_0%,transparent_55%),radial-gradient(50%_50%_at_90%_10%,hsl(153_60%_45%/0.14)_0%,transparent_60%)]",
        "Subtle top border glow: before:content-[''] before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-[linear-gradient(90deg,transparent,hsl(220_86%_60%/0.35),transparent)]"
      ],
      "noise": {
        "approach": "Add a reusable `bg-noise` utility via CSS with a tiny SVG data-uri; apply at 6–10% opacity on large surfaces.",
        "do_not": "Do not place noise over dense tables; use only on page background or hero bands."
      }
    }
  },

  "spacing_grid_and_density": {
    "base": "Use 4px grid; default paddings 16–24; section gaps 24–40",
    "dashboard_density": {
      "tables": "row height 44–48px; keep text-sm; show secondary metadata in text-xs",
      "cards": "p-4 sm:p-5; avoid over-padding to keep dense",
      "forms": "label text-xs, input h-10, helper text-xs"
    },
    "guest_density": {
      "cards": "p-4; big tap targets (min-h-11)",
      "category_chips": "scrollable horizontal, gap-2"
    }
  },

  "components": {
    "shadcn_primary_components": {
      "navigation": [
        {"name":"Sheet","path":"/app/frontend/src/components/ui/sheet.jsx","use":"Mobile nav + filters drawer"},
        {"name":"NavigationMenu","path":"/app/frontend/src/components/ui/navigation-menu.jsx","use":"Optional top-level admin sections (desktop)"},
        {"name":"Breadcrumb","path":"/app/frontend/src/components/ui/breadcrumb.jsx","use":"Admin deep pages"}
      ],
      "structure": [
        {"name":"Resizable","path":"/app/frontend/src/components/ui/resizable.jsx","use":"Inbox tri-pane + CRM inspector"},
        {"name":"ScrollArea","path":"/app/frontend/src/components/ui/scroll-area.jsx","use":"Conversation list, boards, menu categories"},
        {"name":"Separator","path":"/app/frontend/src/components/ui/separator.jsx","use":"Pane dividers + list separators"}
      ],
      "data_display": [
        {"name":"Card","path":"/app/frontend/src/components/ui/card.jsx","use":"KPI tiles, guest request cards, menu item cards"},
        {"name":"Table","path":"/app/frontend/src/components/ui/table.jsx","use":"Users/Roles, Rooms/Tables, Loyalty ledger"},
        {"name":"Tabs","path":"/app/frontend/src/components/ui/tabs.jsx","use":"Requests/Orders board views; CRM sections"},
        {"name":"Badge","path":"/app/frontend/src/components/ui/badge.jsx","use":"Status chips + tags"},
        {"name":"Progress","path":"/app/frontend/src/components/ui/progress.jsx","use":"SLA countdown + order prep"},
        {"name":"Skeleton","path":"/app/frontend/src/components/ui/skeleton.jsx","use":"List loading states"}
      ],
      "inputs": [
        {"name":"Input","path":"/app/frontend/src/components/ui/input.jsx","use":"Search, forms"},
        {"name":"Textarea","path":"/app/frontend/src/components/ui/textarea.jsx","use":"Notes, chat compose"},
        {"name":"Select","path":"/app/frontend/src/components/ui/select.jsx","use":"Department/Status filters"},
        {"name":"Checkbox","path":"/app/frontend/src/components/ui/checkbox.jsx","use":"Bulk selection"},
        {"name":"Switch","path":"/app/frontend/src/components/ui/switch.jsx","use":"Feature flags"},
        {"name":"Calendar","path":"/app/frontend/src/components/ui/calendar.jsx","use":"Date filters, loyalty expiry"}
      ],
      "overlays": [
        {"name":"Dialog","path":"/app/frontend/src/components/ui/dialog.jsx","use":"Create/edit entities"},
        {"name":"Drawer","path":"/app/frontend/src/components/ui/drawer.jsx","use":"Mobile order details / request details"},
        {"name":"Popover","path":"/app/frontend/src/components/ui/popover.jsx","use":"Quick actions"},
        {"name":"Tooltip","path":"/app/frontend/src/components/ui/tooltip.jsx","use":"Icon-only controls"},
        {"name":"DropdownMenu","path":"/app/frontend/src/components/ui/dropdown-menu.jsx","use":"Row actions"},
        {"name":"AlertDialog","path":"/app/frontend/src/components/ui/alert-dialog.jsx","use":"Destructive confirms"}
      ],
      "feedback": [
        {"name":"Sonner","path":"/app/frontend/src/components/ui/sonner.jsx","use":"All toasts"},
        {"name":"Alert","path":"/app/frontend/src/components/ui/alert.jsx","use":"Inline errors/warnings"}
      ]
    },

    "page_level_compositions_to_build": {
      "login": {
        "layout": "Split minimal: left brand + value props, right auth card (on mobile: single card)",
        "components": ["Card", "Input", "Button", "Separator"],
        "microcopy": "‘Night-shift ready. Fast triage across channels.’"
      },
      "admin_overview": {
        "layout": "Top KPI row (4 cards) + activity feed + SLA chart",
        "charts": "Use Recharts (area + bar) with dark-friendly strokes.",
        "components": ["Card", "Tabs", "Table", "Badge"]
      },
      "inbox_agent_view": {
        "layout": "Resizable tri-pane: conversations list + chat + AI assist inspector",
        "ai_panel": "Right side: ‘Suggested reply’, ‘Knowledge snippets’, ‘Next best action’, confidence + citations",
        "keyboard": "Add ⌘K command palette (use shadcn Command) for jump to conversation/contact."
      },
      "requests_board": {
        "layout": "Kanban columns with sticky column headers and counters",
        "interaction": "Drag/drop optional (phase 2). For now: quick status dropdown + optimistic UI.",
        "components": ["Tabs", "Card", "Badge", "DropdownMenu", "ScrollArea"]
      },
      "orders_board": {
        "layout": "Two modes: (1) Kanban (RECEIVED/PREPARING/SERVED), (2) Table (dense) toggle",
        "components": ["Tabs", "Table", "Badge", "Drawer"]
      },
      "guest_room_panel": {
        "layout": "Hotel-branded header band + request composer + current requests timeline",
        "components": ["Card", "Textarea", "Select", "Progress", "Badge"],
        "details": "Show request status with stepper-like chips (Submitted → Assigned → Resolved)."
      },
      "guest_table_panel": {
        "layout": "Menu categories sticky at top; item cards; cart bottom bar; order tracking",
        "components": ["Tabs", "Card", "Button", "Drawer", "ScrollArea"],
        "upsell": "Add ‘Popular with your table’ section (small carousel)."
      },
      "crm_contacts": {
        "layout": "List + detail inspector. Detail shows profile, last stays/orders, tags, notes, loyalty.",
        "components": ["Resizable", "Avatar", "Badge", "Tabs", "Textarea"]
      }
    }
  },

  "component_states_and_behaviors": {
    "buttons": {
      "variants": {
        "primary": "bg-primary text-primary-foreground hover:bg-[hsl(var(--primary)/0.9)] focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]",
        "secondary": "bg-secondary text-secondary-foreground hover:bg-[hsl(var(--secondary)/0.9)] border border-border",
        "ghost": "hover:bg-accent text-foreground",
        "destructive": "bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:bg-[hsl(var(--destructive)/0.9)]"
      },
      "shape": "Radius 12px (tokens). Default height h-10; icon buttons h-9 w-9",
      "press": "active:scale-[0.98] transition-[background-color,box-shadow,opacity] duration-150"
    },
    "inputs": {
      "style": "bg-[hsl(var(--card))] border-border focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]",
      "validation": "Inline text-xs; errors use rose, warnings amber"
    },
    "lists": {
      "row": "hover:bg-[hsl(var(--accent))] focus-within:ring-1 focus-within:ring-[hsl(var(--ring))]",
      "unread": "Left accent bar: before:w-1 before:bg-primary"
    }
  },

  "motion_and_micro_interactions": {
    "library": {
      "recommended": "framer-motion",
      "install": "npm i framer-motion",
      "use_cases": [
        "pane transitions (mobile Sheet/Drawer)",
        "new message pulse",
        "kanban card lift on hover",
        "toast + inline success check"
      ]
    },
    "principles": [
      "Fast, restrained: 150–220ms for hover; 220–320ms for panel transitions",
      "Use easing: cubic-bezier(0.2, 0.8, 0.2, 1)",
      "Never animate layout continuously in dense tables"
    ],
    "examples": {
      "hover_lift_card": "hover:translate-y-[-1px] hover:shadow-[0_10px_30px_-18px_rgba(0,0,0,0.8)] transition-[box-shadow,background-color] duration-200",
      "new_activity_pulse": "animate-[pulse_1.2s_ease-in-out_2]"
    }
  },

  "data_viz": {
    "library": {
      "recommended": "recharts",
      "install": "npm i recharts"
    },
    "dark_theme_chart_rules": [
      "Grid strokes: hsl(var(--border))",
      "Axis text: hsl(var(--muted-foreground))",
      "Primary series: hsl(var(--primary))",
      "Success series: hsl(var(--success))",
      "Warnings: hsl(var(--warning))",
      "Tooltips: use shadcn Card styles (bg-card border-border)"
    ]
  },

  "i18n_and_content": {
    "direction": "LTR (EN/TR)",
    "guidelines": [
      "Avoid hard-coded widths; TR strings can be ~15–25% longer.",
      "Use sentence case labels; keep verbs consistent (Assign, Resolve, Snooze)."
    ]
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast for text on dark surfaces",
      "Visible focus states on all controls (ring token)",
      "Min tap target 44x44 on guest panels",
      "Use `aria-label` for icon-only buttons",
      "Respect prefers-reduced-motion: disable non-essential animations"
    ]
  },

  "testing_attributes": {
    "rule": "All interactive + key informational UI elements MUST include data-testid.",
    "examples": [
      "data-testid=\"login-email-input\"",
      "data-testid=\"inbox-conversation-list\"",
      "data-testid=\"chat-compose-send-button\"",
      "data-testid=\"requests-board-column-open\"",
      "data-testid=\"guest-menu-add-to-cart-button\"",
      "data-testid=\"loyalty-ledger-table\""
    ],
    "naming": "kebab-case; describe role not appearance"
  },

  "image_urls": {
    "guest_room_header": [
      {
        "url": "https://images.unsplash.com/photo-1560844055-d36b1bdcfec2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2OTV8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBob3RlbCUyMGxvYmJ5JTIwbmlnaHQlMjBpbnRlcmlvcnxlbnwwfHx8Ymx1ZXwxNzcwNDk1NDY2fDA&ixlib=rb-4.1.0&q=85",
        "description": "Abstract luxury corridor; use as blurred hero band in room panel"
      },
      {
        "url": "https://images.unsplash.com/photo-1572525621554-9013384b1d36?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2OTV8MHwxfHNlYXJjaHwyfHxsdXh1cnklMjBob3RlbCUyMGxvYmJ5JTIwbmlnaHQlMjBpbnRlcmlvcnxlbnwwfHx8Ymx1ZXwxNzcwNDk1NDY2fDA&ixlib=rb-4.1.0&q=85",
        "description": "Blue lounge; good fallback header image"
      }
    ],
    "guest_table_header": [
      {
        "url": "https://images.unsplash.com/photo-1650211577447-c2d73ed26236?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwxfHxyZXN0YXVyYW50JTIwbmlnaHQlMjBpbnRlcmlvcnxlbnwwfHx8cmVkfDE3NzA0OTU0NzR8MA&ixlib=rb-4.1.0&q=85",
        "description": "Moody restaurant neon; blur + dark overlay; keep subtle"
      }
    ],
    "admin_empty_states": [
      {
        "url": "https://assets.vercel.com/image/upload/v1663633861/nextjs/learn/starter/placeholder.png",
        "description": "TEMP placeholder; replace later with custom monochrome illustrations"
      }
    ]
  },

  "instructions_to_main_agent": [
    "Remove CRA default App.css centering patterns; do not use `.App-header` layout. Build a proper shell with left nav + content.",
    "Set dark-only theme by applying `className=\"dark\"` on the root html/body wrapper (e.g., in index.js or App root).",
    "Replace shadcn color tokens in /frontend/src/index.css with the provided dark tokens. Ensure `--primary` is indigo/blue; add `--success`, `--warning` tokens and use via Tailwind arbitrary values where needed.",
    "Use shadcn components from `/src/components/ui/*.jsx` only; do not introduce raw HTML dropdown/calendar/toast implementations.",
    "Implement Inbox tri-pane with `ResizablePanelGroup`: conversation list left, chat middle, AI inspector right. Mobile uses Sheet/Drawer.",
    "Every button/input/link/list row that is clickable MUST include `data-testid` (kebab-case).",
    "Add Recharts for admin KPIs (SLA, volume, resolution time).",
    "Add framer-motion for small motion only; no `transition: all` anywhere."
  ],

  "component_path": {
    "shadcn_ui_dir": "/app/frontend/src/components/ui",
    "note": "Project uses .jsx (not .tsx). Ensure guidelines and new components follow named export convention."
  }
}

---

<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>
