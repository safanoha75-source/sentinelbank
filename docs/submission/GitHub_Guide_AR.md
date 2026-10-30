# رفع المشروع إلى GitHub - خطوات آمنة

## قبل البدء
- يجب أن تكوني داخل `D:\datasetfruad`.
- انسخي ملفات README.md و.gitignore وrequirements-dashboard.txt و.env.example وrender.yaml وDockerfile.render من هذه الحزمة إلى جذر المشروع.
- ضعي ملفات التوثيق والعرض في مجلد docs/presentation داخل المشروع أو ارفعيها كمرفقات Release.
- راجعي `.gitignore` وتأكدي من استثناء `.venv`, `.env`, كلمات المرور، ملفات CSV الخام الكبيرة، وملفات قاعدة البيانات.
- لا ترفعي `fraud_sgd_bundle.joblib` أو parquet الكبير إلا إذا كانت سياسة المشروع تسمح بذلك؛ استخدمي Git LFS أو مكانًا منفصلًا للـartifacts عند الحاجة.

## أوامر PowerShell من جذر D:\datasetfruad

```powershell
git status
git init
git add README.md .gitignore requirements-dashboard.txt .env.example render.yaml Dockerfile.render src sql docs reports
git status
git commit -m "Prepare PaySim fraud intelligence project submission"
git branch -M main
```

ثم أنشئي Repository فارغًا في GitHub، وانسخي رابط HTTPS الخاص به، ثم نفذي (استبدلي الرابط فقط):

```powershell
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

إذا كان remote موجودًا مسبقًا، افحصيه باستخدام `git remote -v` ولا تضيفيه مرة ثانية. لا تستخدمي `git add .` قبل مراجعة `git status`؛ هذا يمنع رفع ملفات كبيرة أو أسرار بالخطأ.

## ما الذي ترسلينه في التسليم؟
1. Documentation link: رابط PDF التوثيق أو مجلد Docs في GitHub.
2. GitHub link: رابط المستودع العام أو المصرح للمقيّمين.
3. Presentation link: رابط PDF الشرائح ورابط فيديو MP4 بعد رفعه.
