# apple_login - Sign in with Apple for Odoo 18
## Uellow Custom Module

---

## 📋 المتطلبات

### 1. Python Dependencies (داخل Docker)
```bash
docker exec odoo-docker-web-1 pip install PyJWT cryptography requests --break-system-packages
```

### 2. نسخ المديول
```bash
cp -r apple_login /root/odoo-docker/uellowcom/
```

### 3. تثبيت المديول
```bash
docker exec odoo-docker-web-1 odoo -u apple_login -d odoo --stop-after-init --no-http
```

---

## 🍎 إعداد Apple Developer

### الخطوات المطلوبة في Apple Developer Portal:

#### أ. إنشاء App ID
1. اذهب إلى [developer.apple.com](https://developer.apple.com)
2. **Certificates, IDs & Profiles** → **Identifiers**
3. أنشئ **App ID** جديد واختر **Sign In with Apple**

#### ب. إنشاء Services ID (Client ID)
1. **Identifiers** → **+** → اختر **Services IDs**
2. وصف مثل: `Uellow Sign In`
3. Identifier مثل: `com.uellow.signin` ← هذا هو **Client ID**
4. فعّل **Sign In with Apple** واضغط **Configure**
5. أضف Redirect URL:
   ```
   https://uellow.com/apple/login/callback
   ```

#### ج. إنشاء Private Key
1. **Keys** → **+** → اختر **Sign In with Apple**
2. حمّل ملف `.p8` ← **احتفظ به جيداً، لن تتمكن من تحميله مرة أخرى**
3. سجّل الـ **Key ID**

#### د. معرفة Team ID
- في أعلى يمين صفحة Developer Portal ← **Team ID** (10 أحرف)

---

## ⚙️ الإعداد في أودو

اذهب إلى: **Settings → General Settings → Sign in with Apple**

| الحقل | القيمة |
|-------|--------|
| Client ID | `com.uellow.signin` |
| Team ID | `XXXXXXXXXX` (10 أحرف) |
| Key ID | `XXXXXXXXXX` (10 أحرف) |
| Private Key | محتوى ملف `.p8` كاملاً |

---

## 🔐 ملاحظات مهمة

1. **Domain Verification**: يجب أن يكون النطاق `uellow.com` موثقاً في Apple Developer
2. **HTTPS إلزامي**: Apple لا تقبل إلا HTTPS
3. **Email Relay**: بعض المستخدمين يخفون بريدهم - نعالج هذا بإنشاء relay email
4. **User Name**: Apple ترسل الاسم **مرة واحدة فقط** عند أول تسجيل دخول
5. **تسجيل جديد**: يعمل فقط إذا كانت الـ Settings → `auth_signup.invitation_scope = b2c`

---

## 🧪 اختبار

```bash
# تفعيل اختبار في المتصفح
# اذهب إلى: https://uellow.com/web/login
# ستجد زر "تسجيل الدخول بـ Apple" تحت الفورم
```

---

## 🐛 Debug

```bash
# مراقبة الـ logs
docker logs odoo-docker-web-1 -f | grep -i apple
```
