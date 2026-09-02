# AMAN — أمان

بوت Telegram لإدارة حماية ومتابعة أرقام الهاتف اليمنية، الاشتراكات، المدفوعات، الدعم، الإشعارات، المتابعات والإدارة بصلاحيات RBAC.

## Stack

- Python 3
- `python-telegram-bot==21.10`
- SQLAlchemy 2 Async + `asyncpg` + PostgreSQL / Supabase PostgreSQL
- Alembic migrations حقيقية
- APScheduler 3.10.4
- PostgreSQL-authoritative FSM في `fsm_states`
- ReplyKeyboard للتنقل الأساسي
- Customer Mode يستخدم customer handlers/services نفسها
- Sandbox بقاعدة PostgreSQL منفصلة عبر `SANDBOX_DATABASE_URL`

## Local setup

1. أنشئ PostgreSQL للإنتاج، وقاعدة PostgreSQL منفصلة للـSandbox عند الحاجة.
2. انسخ `.env.example` إلى `.env`.
3. اضبط `BOT_TOKEN`, `DATABASE_URL`, و`ADMIN_IDS`.
4. اضبط `SANDBOX_DATABASE_URL` على قاعدة مختلفة فعليًا إذا أردت Sandbox.
5. ثبّت الاعتمادات:

```bash
pip install -r requirements.txt
```

6. نفّذ migration:

```bash
alembic upgrade head
```

وللـSandbox:

```bash
DATABASE_URL="$SANDBOX_DATABASE_URL" alembic upgrade head
```

7. شغّل:

```bash
python main.py
```

التطبيق لا يستخدم `Base.metadata.create_all()` في startup. الـschema الإنتاجي يُدار بواسطة Alembic.

## Environment variables

انظر `.env.example`. الأسرار لا تُحفظ داخل المستودع.

`notification_max_attempts` ليس Environment Variable تشغيليًا؛ مصدره الوحيد هو جدول `system_settings` حتى يصبح تعديل الإدارة فعالًا دون restart.

## Render + Supabase

استخدم Render Worker لأن التطبيق يعمل Telegram polling. `scripts/start.sh`:

1. ينفذ `alembic upgrade head` على Production.
2. إذا كان `SANDBOX_DATABASE_URL` مختلفًا عن `DATABASE_URL`، ينفذ نفس migration على Sandbox.
3. يشغل `python main.py`.

ضع الأسرار والقيم التشغيلية في Render Environment Variables، ولا تضعها في `render.yaml`.

## Database / migrations

المصدر الوظيفي للـschema هو:

`app/models.py` ↔ `migrations/versions/0001_initial.py` ↔ `migrations/versions/0002_notification_leases.py` ↔ `migrations/final_schema.sql`

`final_schema.sql` تم توليده من Alembic offline بعد الإصلاحات، ويحتوي على PostgreSQL ENUMs والجداول والقيود والفهارس وحقول notification leases.

## FSM

الحالة الأساسية محفوظة في PostgreSQL. عند كل Telegram Update يتم تحميل `current_state` و`state_data` من `fsm_states`، ويستخدم `context.user_data` كنسخة عمل مؤقتة فقط.

في Production يستخدم FSM قفل PostgreSQL transaction-scoped لكل Telegram ID لمنع تحديثات المستخدم المتزامنة من الكتابة فوق بعضها. بعد restart تتم استعادة الحالة من PostgreSQL.

## Payments

اعتماد الدفع يتم داخل transaction واحدة:

`lock payment → approve → subscription → phone → followup → notification record → audit → commit`

ولا تُرسل Telegram API داخل transaction المالية. رسالة العميل بعد نجاح المعاملة تأتي من notification queue.

المال يستخدم `Decimal` وPostgreSQL `NUMERIC(18,2)`.

## Notifications

الإشعارات تستخدم:

- unique dedupe key
- PostgreSQL `FOR UPDATE SKIP LOCKED`
- atomic claim
- processing lease
- retry/backoff
- recovery بعد crash
- حد محاولات واحد من `system_settings`

التسليم مع Telegram هو **at-least-once** عمليًا؛ لا يتم الادعاء بـexactly-once لأن Telegram API لا يوفر idempotency key لهذا الاستخدام. إذا حدث crash بعد قبول Telegram للرسالة وقبل تسجيل `sent_at`، يمكن إعادة المحاولة بعد انتهاء الـlease.

## Scheduler

- Subscription warnings: 30 / 7 / 3 / 1 day windows.
- Followup cycle: configurable، افتراضيًا 90 يومًا.
- Notification delivery: كل دقيقة.

حساب التحذيرات يعتمد على `timedelta` ونوافذ شاملة حتى لا يضيع تنبيه بسبب ثانية واحدة أو تأخر تشغيل الـjob. Dedupe يمنع إعادة إنشاء نفس الإشعار.

## Sandbox

Sandbox يستخدم قاعدة PostgreSQL منفصلة. بيانات العملاء/الأرقام/المدفوعات/الاشتراكات/الدعم في Sandbox لا تُكتب إلى Production.

حالة mode/FSM الصغيرة محفوظة في Production لاستعادة وضع المدير. إذا حدث crash بعد commit للـSandbox وقبل حفظ mode pointer، تبقى بيانات Sandbox معزولة وقابلة لإعادة استخدامها أو تنظيفها لاحقًا؛ لا يتم تحويلها إلى Production.

## Admin / RBAC

الأدوار:

- `super_admin`
- `finance`
- `support`
- `operations`
- `viewer`

التحقق من الصلاحيات server-side داخل handlers/services، وليس مجرد إخفاء الأزرار.

`👤 وضع العميل` يعيد استخدام تجربة العميل الحقيقية. `A` أو `a` يعيد المدير إلى Admin Mode بعد تحقق من صلاحية المدير.

## Security

- لا توجد secrets حقيقية في الحزمة.
- `.env` مستثنى من Git.
- `.env.example` يحتوي placeholders فقط.
- لا يوجد SQLite/Redis/MongoDB.
- أخطاء النظام لا تعرض stack traces للمستخدم.
- audit trail لا يخزن نص رد الدعم؛ محتوى الرسالة يبقى في `support_messages`، بينما audit يسجل metadata فقط.

## Testing

الاختبارات المحلية:

```bash
python -m compileall .
pytest -q
```

وتوجد مجموعة PostgreSQL حقيقية في `tests/test_real_postgres.py`. لا تستخدم SQLite كبديل. لتشغيلها يجب توفير قاعدة اختبار PostgreSQL مخصصة عبر:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://... pytest -q
```

في بيئة الإصدار الحالية لا يوجد PostgreSQL server ولا `asyncpg` ولا `python-telegram-bot` ولا APScheduler مثبتة، لذلك اختبارات PostgreSQL وTelegram runtime لم تُنفذ هنا.

راجع `FINAL_AUDIT.md` لمعرفة ما تم إثباته فعليًا وما بقي محجوبًا بقيود البيئة.
