# api-operator vNext — خطة العمل التفصيلية

> **Safe API Agent:** وكيل ذكاء اصطناعي يشغّل الـ APIs بأمان داخل بيئات SaaS متعددة المستأجرين.  
> المستند هذا هو المرجع التنفيذي للقرار والمراحل والدمج مع المشاريع الحالية.

| الحقل | القيمة |
|--------|--------|
| المنتج | `api-operator` (ريبو مستقل — موجود) |
| الإصدار الحالي | `0.10.0` (PyPI) |
| الإصدار المستهدف للمرحلة 1 | `1.0.0` |
| اللغة | Python 3.11+ |
| أول عميل تكامل | [laravel-tenant-kit](https://github.com/mohammedelkarsh/laravel-tenant-kit) |
| تاريخ اعتماد الخطة | 2026-11-23 |
| الحالة | مسودة معتمدة للنقاش → تنفيذ |

---

## 1) القرار الاستراتيجي (ثابت)

### ماذا نعمل؟
نطوّر **`api-operator` الحالي** ليصير منتج AI إنتاجي واضح الهوية:

> **Retrieve (اختياري لاحقًا) → Reason → Act على API بحدود صلاحيات وتكلفة وتدقيق.**

### ماذا لا نعمل؟
- لا نفتح ريبو Laravel AI جديد من الصفر.
- لا ندفن منطق الوكيل داخل `laravel-tenant-kit`.
- لا نجعل RAG هو المنتج الأساسي في الإطلاق الأول.
- لا ننافس أطر RAG العامة (LlamaIndex وأشباهها) وجهاً لوجه.

### ليش مشروع مستقل؟
| السبب | التفصيل |
|--------|---------|
| رواج مثبت | الحزمة منشورة على PyPI وفيها تكامل حي مع tenant-kit |
| جمهور أوسع | أي REST API وليس Laravel فقط |
| نمط ناجح عندنا | مثل `kyc-ai/laravel`: core مستقل + تكامل opt-in |
| عزل المخاطر | تجارب AI لا تكسر إصدارات الـ SaaS kit |
| سرعة الإصدار | Semver خاص بـ api-operator بدون انتظار tenant-kit |

### كيف نستفيد في مشاريعنا الحالية؟
```
api-operator (مستقل — المنتج AI)
        │
        ├── adapter رسمي → laravel-tenant-kit
        ├── tools لاحقًا → kyc-ai / billing / webhooks
        └── نفس الـ runtime → أي منتج SaaS لاحق
```

- **tenant-kit:** وكيل أذكى + أأمن + مربوط بـ `agent_calls` والفوترة.
- **kyc-ai:** لاحقًا أدوات قراءة/إعادة تشغيل تحقق ضمن صلاحيات.
- **أي منتج جديد:** يعيد استخدام نفس الـ operator بدون إعادة اختراع.

---

## 2) الوضع الحالي (Baseline — 0.10.0)

ما هو موجود اليوم ويجب البناء فوقه لا استبداله:

| المكوّن | الملف/المسار | الحالة |
|---------|--------------|--------|
| Agent runtime | `api_operator/core/agent.py` | ✅ يعمل |
| Planner (mock + OpenAI اختياري) | `planner.py`, `planner_openai.py` | ✅ |
| Guardrails أساسية | `guardrails.py` (abilities + confirm dangerous) | ✅ جزئي |
| Tool executor | `executor.py` | ✅ |
| YAML adapter | `adapters/yaml_adapter.py` | ✅ |
| OpenAPI generator | `adapters/openapi_generator.py` | ✅ |
| CLI + HTTP server | `server/cli.py`, `server/app.py` | ✅ |
| Tenant-kit example | `examples/tenant-kit-adapter/` | ✅ |
| Keyword RAG بسيط | `rag/indexer.py` (بدون embeddings) | ✅ تجريبي خفيف |
| Policy engine متقدم | — | ❌ غير موجود |
| Quotas / budgets | — | ❌ غير موجود |
| Audit log إنتاجي | — | ❌ غير موجود |
| Dry-run mode | — | ❌ غير موجود |
| Vector RAG / pgvector | — | ❌ غير موجود |

**الخلاصة:** الأساس قوي. الفجوة الحقيقية للسوق هي طبقة **الأمان التشغيلي + التكلفة + التدقيق** قبل أي RAG متقدم.

---

## 3) الرؤية المستهدفة

### جملة المنتج
`api-operator` يحوّل أي OpenAPI/`adapter.yaml` إلى وكيل يستطيع:

1. فهم طلب المستخدم.
2. اختيار الأداة المناسبة.
3. التحقق من الصلاحية والميزانية.
4. (اختياري) استعراض معرفة مرتبطة بالـ docs.
5. التنفيذ أو الرفض أو طلب تأكيد.
6. تسجيل كل خطوة في audit trail.

### مبادئ التصميم
1. **Core خفيف** — لا يفرض Laravel ولا Postgres ولا مزوّد embeddings.
2. **Adapters اختيارية** — OpenAPI/YAML أولاً؛ Knowledge لاحقًا كـ extra.
3. **Secure by default** — الأدوات الخطرة تحتاج تأكيد؛ السياسات تُرفض افتراضيًا إن نقصت الصلاحية.
4. **Observable** — كل action له أثر قابل للمراجعة والفوترة.
5. **Tenant-aware hooks** — الـ core لا يعرف tenancy، لكن يمرّر `tenant_id` / `abilities` / `quota_context` من المضيف.

---

## 4) خارطة الإصدارات

| الإصدار | الاسم الداخلي | الهدف | أين يتم العمل |
|---------|---------------|--------|----------------|
| **0.11.x** | Foundation | سياسات + dry-run + audit hooks بدون كسر توافق | `api-operator` فقط |
| **1.0.0** | Safe API Agent | منتج إنتاجي معلن: policy + quota + audit + docs | `api-operator` |
| **1.0.x + tenant-kit** | First-class integration | دمج opt-in مع الكيت والعدادات | `api-operator` + `laravel-tenant-kit` |
| **1.1.0** | Knowledge (RAG) | RAG اختياري: keyword→embeddings→pgvector | `api-operator` (+ extra) |
| **1.2+** | Ecosystem | أدوات KYC/billing أعمق، مزوّدات vector إضافية | حسب الطلب |

> ملاحظة: أرقام 0.11 قد تُدمج مباشرة في 1.0.0 إذا كان حجم التغيير يستحق قفزة major واضحة. القرار النهائي عند بدء التنفيذ حسب كسر التوافق.

---

## 5) المرحلة 0 — التحضير (يوم واحد)

**الهدف:** تثبيت النطاق قبل كتابة كود الميزة.

### المهام بالترتيب
1. اعتماد هذا المستند كمرجع (`docs/ROADMAP-vNEXT.md`).
2. فتح Issue/Milestone على ريبو `api-operator` بعنوان: `v1.0 Safe API Agent`.
3. جرد سريع لما هو مستخدم من الـ public API الحالي حتى لا نكسر adapters موجودة.
4. تعريف عقود البيانات الأساسية (مسودات schemas):
   - `PolicyDecision`
   - `QuotaReservation`
   - `AuditEvent`
   - `DryRunReport`
5. تحديث جملة الـ README لاحقًا (بعد وجود كود) لتعكس الهوية الجديدة بدون حذف التوافق الحالي.

### تعريف الإنجاز (Done)
- [x] المستند موجود في الريبو.
- [x] Milestone جاهز بالمهام أدناه.
- [x] اتفاق: RAG خارج 1.0.0.

---

## 6) المرحلة 1 — منتج مستقل `1.0.0` (1–2 أسابيع)

**المكان:** ريبو `api-operator` فقط.  
**لا تعديل إلزامي على tenant-kit في هذه المرحلة** (ما عدا ملاحظات توافق إن لزم).

### 6.1 Policy Engine (أولوية قصوى)

**المشكلة:** اليوم يوجد `requires_ability` و`dangerous` فقط. هذا لا يكفي لـ SaaS حقيقي.

**ما نبنيه:**
- ملف سياسة اختياري بجانب الـ adapter، مثال: `policy.yaml`
- قواعد من نوع:
  - السماح/المنع حسب `ability`
  - منع أدوات حسب الدور أو الـ tenant
  - حد أقصى لاستدعاءات أداة معيّنة في الجلسة
  - إجبار confirmation على مجموعات أدوات (ليس فقط `dangerous: true`)
- نتيجة قرار موحّدة: `allow` | `deny` | `confirm`

**التكامل في التدفق:**
```
User message
  → Planner يختار tool
  → PolicyEngine.check(...)
  → (deny) رجوع برسالة واضحة
  → (confirm) طلب تأكيد
  → (allow) Executor
```

**ملفات متوقعة:**
- `api_operator/core/policy.py`
- `api_operator/core/policy_schema.py` (أو نماذج Pydantic داخل policy)
- اختبارات: `tests/test_policy.py`

**Done:**
- [x] سياسة تُحمَّل من YAML.
- [x] الرفض يظهر في CLI وHTTP بنفس الشكل.
- [x] اختبارات تغطي allow/deny/confirm.

---

### 6.2 Dry-run mode

**المشكلة:** المستخدم/المطور يريد أن يرى ماذا سيفعل الوكيل قبل التنفيذ الفعلي.

**ما نبنيه:**
- خيار `--dry-run` في CLI.
- باراميتر `dry_run=true` في `/v1/chat`.
- عند التفعيل: التخطيط + فحص السياسة + **بدون** HTTP حقيقي للأدوات.
- رد يتضمن: الأداة المختارة، المدخلات، قرار السياسة، وما كان سيُرسل للـ API.

**Done:**
- [x] dry-run لا يطلق آثار جانبية على الـ API.
- [x] التقرير مقروء للإنسان وللآلة (`DryRunReport`).

---

### 6.3 Audit log

**المشكلة:** بدون أثر تدقيق لا يمكن بيع هذا لـ SaaS جاد.

**ما نبنيه:**
- واجهة `AuditSink` (protocol):
  - تنفيذ افتراضي: كتابة JSON lines إلى ملف/stdout
  - تنفيذ اختياري لاحقًا: HTTP webhook / Laravel callback
- كل حدث يسجّل على الأقل:
  - `timestamp`
  - `session_id`
  - `adapter`
  - `tool`
  - `arguments` (مع redaction للحقول الحساسة)
  - `decision` (allow/deny/confirm)
  - `result_status`
  - `duration_ms`
  - `tenant_id` / `actor_id` إن وُجدت في السياق

**ملفات متوقعة:**
- `api_operator/core/audit.py`
- `api_operator/core/redaction.py`
- `tests/test_audit.py`

**Done:**
- [x] كل تنفيذ/رفض ينتج `AuditEvent`.
- [x] إمكانية تعطيل التدقيق بعلم إعداد (افتراضي: مفعّل في الإنتاج المقترح).
- [x] redaction للمفاتيح الشائعة: `password`, `token`, `secret`, `authorization`.

---

### 6.4 Quota / budget hooks

**المشكلة:** الـ AI بدون سقف تكلفة خطر على المنتج.

**ما نبنيه (في الـ core — بدون فرض Stripe):**
- واجهة `QuotaGateway`:
  - `check(context, estimated_cost) -> allow|deny`
  - `commit(context, actual_cost)`
  - `rollback(...)` عند الفشل إن لزم
- تنفيذ محلي بسيط في الذاكرة/الملف للتجارب.
- حقول تكلفة تقديرية قابلة للضبط:
  - per-tool cost weight
  - optional LLM token usage من الـ planner

**ملاحظة مهمة:** الفوترة الحقيقية تبقى عند المضيف (مثل tenant-kit `agent_calls`). الـ operator يوفر الـ hooks فقط.

**Done:**
- [x] عند تجاوز الحصة: رفض واضح قبل التنفيذ.
- [x] اختبارات mock لـ QuotaGateway.
- [x] توثيق كيف يربطها تطبيق Laravel لاحقًا.

---

### 6.5 تحسين OpenAPI → tools (صقل موجود)

**الموجود:** `generate-from-openapi`.  
**التحسين المطلوب لـ 1.0:**
- وسم أدوات الكتابة (`POST/PATCH/DELETE`) كـ `dangerous` افتراضيًا عند التوليد.
- اقتراح abilities افتراضية من tags المسار إن أمكن.
- توليد هيكل `policy.yaml` اختياري مع الـ adapter.

**Done:**
- [x] المولّد يخرج adapter + مسودة سياسة.
- [x] مثال واحد غير tenant-kit (API عام بسيط) في `examples/`.

---

### 6.6 توثيق وإصدار 1.0.0

**المهام:**
1. [x] تحديث `README.md` بهوية Safe API Agent.
2. [x] تحديث `CHANGELOG.md` لقسم `0.11.0` (سيتم دمجه/ترقيته إلى `1.0.0` عند النشر).
3. [x] صفحة docs قصيرة:
   - `docs/policy.md`
   - `docs/audit.md`
   - `docs/quotas.md`
   - `docs/dry-run.md`
4. [x] نشر PyPI `api-operator==0.11.0` (Foundation؛ قفزة `1.0.0` لاحقًا عند الجاهزية).
5. [x] Tag Git `v0.11.0` (و`v1.0.0` عند الـ major).

**Done للمرحلة 1 كاملة:**
- [x] Policy + Dry-run + Audit + Quota hooks تعمل معًا في مسار chat واحد.
- [x] الاختبارات الخضراء على CI.
- [x] لا يوجد اعتماد إجباري على Laravel أو vector DB.
- [x] الحزمة منشورة: `pip install api-operator==0.11.0` — https://pypi.org/project/api-operator/0.11.0/

---

## 7) المرحلة 2 — الدمج مع laravel-tenant-kit (≈ أسبوع)

**المبدأ:** tenant-kit يبقى PHP-only؛ الـ operator sidecar كما هو اليوم.  
الدمج = adapter + إعدادات + عدّادات + تجربة مستخدم أفضل، **بدون** `composer require` للـ AI.

### 7.1 مزامنة الـ adapter
- تحديث `laravel-tenant-kit/integrations/api-operator/adapter.yaml`
- مزامنة المرآة في `api-operator/examples/tenant-kit-adapter/`
- إضافة `policy.yaml` خاص بأدوات الكيت (workspaces/team/usage)

### 7.2 ربط الصلاحيات والـ tenant context
- تمرير `abilities` من توكن Sanctum / المستخدم الحالي إلى `/v1/chat`
- تمرير `tenant_id` / `workspace_id` في metadata الجلسة
- التأكد أن أدوات الـ subdomain ما زالت تعمل مع `connect_host`

### 7.3 ربط الاستخدام والفوترة
- عند كل tool call ناجح: زيادة عدّاد `agent_calls` (الموجود في roadmap الكيت)
- إعداد اختياري لرفض الطلبات عند تجاوز خطة الـ workspace
- توثيق المتغيرات في `.env.example` للكيت

### 7.4 تجربة المنتج داخل الكيت
- الشات الموجّه الحالي يستخدم dry-run عند الحاجة
- رسائل أوضح عند deny بسبب policy/quota
- تحديث `docs/api-operator.md` و`docs/ROADMAP.md` في الكيت

### 7.5 اختبارات
- تحديث اختبارات الـ adapter في الطرفين
- سيناريو تكامل:  
  `list_workspaces` مسموح → `create_workspace` يحتاج confirm → تجاوز quota يُرفض

**Done للمرحلة 2:**
- [x] التكامل opt-in (افتراضي آمن إن كان العامل معطّلًا).
- [x] الوثائق محدّثة في الكيت.
- [x] إصدار tenant-kit patch يذكر دعم `api-operator>=0.11` (PR #36 → v1.5.3).
- [x] لا كسر لتثبيتات الكيت التي لا تستخدم الـ operator.

---

## 8) المرحلة 3 — RAG / Vector Knowledge (بعد ثبات 1.0)

**الهدف:** معرفة تساعد الوكيل على الاختيار الصحيح — ليست منتجًا مستقلًا.

### 8.1 لماذا بعد 1.0؟
- السوق يحتاج أمان التشغيل قبل “بحث دلالي”.
- عندنا أصلًا `DocsIndex` كبداية keyword.
- إدخال embeddings مبكرًا يزيد التعقيد والتكلفة قبل إثبات القيمة.

### 8.2 طبقات RAG المقترحة

| الطبقة | التقنية | متى |
|--------|---------|-----|
| L0 (موجود) | Keyword chunks على ملفات docs | الآن / تحسين بسيط مع 1.0 إن لزم |
| L1 | Embeddings + تخزين محلي بسيط | 1.1.0 |
| L2 | Postgres + pgvector (موصى به لـ Laravel SaaS) | 1.1.0 extra |
| L3 | Pinecone / Qdrant drivers | 1.2+ اختياري |

### 8.3 نطاق معرفة الوكيل (بالترتيب)
1. وثائق الـ adapter / OpenAPI descriptions  
2. README وسياسات المنتج للمضيف  
3. معرفة per-tenant (FAQ/سياسات العميل) مع عزل صارم  
4. لاحقًا: مستندات KYC/تشغيل إن ظهرت حاجة

### 8.4 تدفق الاستخدام
```
User message
  → Knowledge.retrieve(query, tenant_scope)
  → Planner يستلم excerpts كسياق
  → Policy + Quota كما في 1.0
  → Execute
```

### 8.5 Extra بايثون مقترح
```toml
[project.optional-dependencies]
llm = ["openai>=1.35.0"]
rag = ["pgvector...", "sqlalchemy..."]  # يُحدد بدقة عند التنفيذ
```

**Done للمرحلة 3:**
- [x] RAG معطّل افتراضيًا.
- [x] عزل tenant على مستوى الفهرس/الاستعلام.
- [x] مقاييس بسيطة: metadata.knowledge.hits / sources على الرد (تحسين اختيار الأداة يُقاس لاحقًا مع L1).
- [x] وثيقة `docs/knowledge.md`.
- [ ] L1 embeddings + L2 pgvector (ما زال لـ 1.1.0 extra).

---

## 9) الدمج اللاحق مع بقية المنظومة

### laravel-tenant-kit
- أول وأهم عميل.
- يستفيد فورًا من policy/quota/audit.
- يبقى قناة التوزيع الأقوى للـ demo.

### kyc-ai / external-shufti
- بعد استقرار المرحلة 2:
  - أدوات قراءة حالة التحقق
  - إعادة تشغيل job ضمن ability خاصة
  - لا توضع أسرار KYC داخل الـ operator

### أي SaaS لاحق
- نفس الخطوات: `adapter.yaml` + `policy.yaml` + hooks للفوترة.
- لا حاجة لإعادة بناء الوكيل.

---

## 10) خارج النطاق (صراحة)

| العنصر | السبب |
|--------|--------|
| Fine-tuning لنماذج | تكلفة عالية وليست الحاجة الأولى |
| UI Chat جديدة كاملة بديلة لـ Filament | عندنا سطح تكامل كافٍ |
| Laravel package إجباري للـ AI | يكسر استقلال الريبو |
| Multi-agent orchestration معقد | يأجل الـ MVP |
| Vector DB إلزامي في core | يثقل التثبيت |
| استبدال mock planner | يبقى خيارًا رخيصًا للـ demos/tests |

---

## 11) ترتيب التنفيذ اليومي المقترح

### الأسبوع 1 (api-operator)
| يوم | تركيز |
|-----|--------|
| 1 | المرحلة 0 + هيكل `policy` + اختبارات أولية |
| 2 | دمج PolicyEngine في Agent/Executor |
| 3 | Dry-run CLI + HTTP |
| 4 | AuditSink + redaction |
| 5 | QuotaGateway + ربط التكلفة التقديرية |
| 6 | صقل OpenAPI generator + مثال إضافي |
| 7 | Docs + تنظيف + تجهيز 1.0.0 RC |

### الأسبوع 2
| يوم | تركيز |
|-----|--------|
| 1–2 | إصلاحات RC + نشر `1.0.0` |
| 3–5 | المرحلة 2 مع tenant-kit (adapter/policy/usage/docs) |
| 6–7 | اختبار تكامل + إصدار الكيت إن لزم |

### بعد الإطلاق
- جمع ملاحظات الاستخدام
- ثم بدء تصميم المرحلة 3 (RAG) بمواصفات منفصلة قصيرة

---

## 12) معايير النجاح

### نجاح المرحلة 1
- مطوّر يركّب الحزمة على API عشوائي خلال أقل من 30 دقيقة.
- يستطيع منع أداة خطرة بسياسة بدون تعديل كود بايثون.
- لديه سجل تدقيق لكل تنفيذ.

### نجاح المرحلة 2
- مستخدم tenant-kit يرى رفضًا واضحًا عند تجاوز الخطة.
- `agent_calls` يعكس الاستخدام الحقيقي.
- التكامل ما زال opt-in.

### نجاح المرحلة 3
- الوكيل يخطئ أقل في اختيار الأداة بفضل الاسترجاع.
- المعرفة لا تتسرب بين المستأجرين.

---

## 13) مخاطر وتخفيفها

| المخاطر | التخفيف |
|---------|---------|
| تضخم النطاق نحو “منصة AI عامة” | الالتزام بهذا المستند؛ RAG مؤجل |
| كسر adapters حالية | ميزات جديدة opt-in؛ اختبارات رجعية |
| تعقيد tenancy داخل Python | tenancy تبقى عند المضيف؛ نمرّر context فقط |
| تكلفة LLM | الإبقاء على mock planner؛ quotas من اليوم الأول للمسار المدفوع |
| تشتت بين عدة ريبوهات | مرحلة 1 كاملة قبل لمس الكيت بعمق |

---

## 14) قائمة تحقق سريعة للبدء غدًا

1. [x] قراءة واعتماد هذا الملف.
2. [x] إنشاء Milestone `v1.0 Safe API Agent` على GitHub.
3. [x] Issue: Policy Engine  
4. [x] Issue: Dry-run  
5. [x] Issue: Audit log  
6. [x] Issue: Quota hooks  
7. [x] Issue: Docs + release 1.0.0  
8. [x] Issue لاحق (ممنوع في 1.0): Knowledge/RAG  

---

## 15) ملخص تنفيذي بجملة واحدة

> نرفع `api-operator` من مشغّل أدوات مفيد إلى **Safe API Agent مستقل (1.0)**، ثم ندمجه opt-in مع `laravel-tenant-kit`، ثم نضيف RAG كمعرفة مساعدة — بهذا نستفيد من الرواج الحالي وندخل AI/RAG بتسلسل يخدم السوق لا يشتته.

---

## مراجع داخلية

- ريبو الحزمة: `../` (جذر `api-operator`)
- تكامل الكيت: `laravel-tenant-kit/docs/api-operator.md`
- خارطة الكيت: `laravel-tenant-kit/docs/ROADMAP.md`
- نمط الاستقلال الناجح: `kyc-ai/laravel` + opt-in في tenant-kit
- نقطة انطلاق RAG الحالية: `api_operator/rag/indexer.py`
