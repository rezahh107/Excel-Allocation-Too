
# سیستم تخصیص عادلانه دانش‌آموز به پشتیبان (Student-Mentor Assignment)

این پروژه یک اسکریپت پایتون برای مدیریت و تخصیص خودکار دانش‌آموزان به پشتیبان‌ها است. این سیستم با در نظر گرفتن ترجیحات اولیه، محدودیت ظرفیت هر پشتیبان و استفاده از الگوریتم چرخشی (Round Robin) برای توزیع عادلانه باقی‌مانده ظرفیت‌ها، فرآیند تخصیص را بهینه و بدون خطای انسانی انجام می‌دهد.

## ✨ ویژگی‌های کلیدی

- **نرمال‌سازی هوشمند متن**: اصلاح خودکار تفاوت‌های نگارشی فارسی و عربی (مانند تبدیل «ي» به «ی»، «ك» به «ک» و «ة» به «ه») و حذف فاصله‌های اضافی برای تطابق دقیق داده‌ها.
- **مدیریت ظرفیت پویا**: محاسبه خودکار ظرفیت هر پشتیبان بر اساس فرمول `سقف(تعداد کل دانش‌آموزان / تعداد کل پشتیبان‌ها)`.
- **تثبیت و استخر (Stabilization & Pool)**: حفظ تخصیص اولیه دانش‌آموزان تا حد ظرفیت مجاز پشتیبان و انتقال مازاد به یک «استخر» برای توزیع مجدد.
- **تخصیص چرخشی (Round Robin)**: توزیع عادلانه و چرخشی دانش‌آموزان موجود در استخر بین پشتیبان‌هایی که هنوز ظرفیت خالی دارند.
- **اعتبارسنجی داده‌ها (Validation)**: بررسی خودکار صحت تخصیص‌ها (برابری تعداد کل، عدم تجاوز از ظرفیت، و عدم جابه‌جایی دانش‌آموزان تثبیت‌شده).
- **خروجی اکسل ساختاریافته**: تولید فایل اکسل شامل دو شیت «جدول نهایی دانش‌آموزان» و «گزارش آماری» برای شفافیت کامل فرآیند.

## قرارداد مسیر دسکتاپ (PR #1)

ورودی برنامهٔ `app/main.py` دارای پیش‌نمایش، تأیید و خروجی فقط **Excel (.xlsx)** است؛ هیچ فایل HTML جدیدی تولید نمی‌شود. فایل‌های `*_report.html` که از نسخه‌های قدیمی کنار Excel مانده‌اند، حذف یا بازنویسی نمی‌شوند؛ صفحهٔ خروجی دربارهٔ قدیمی بودن و نامعتبر بودن آن‌ها برای تخصیص جاری هشدار می‌دهد. در Excel شیت داده‌ها و شیت «گزارش آماری» باقی می‌مانند. «جابه‌جا شده» یعنی مقدار غیرخالی پشتیبان اولیهٔ واردشده با پشتیبان نهایی (پس از حذف فاصلهٔ کناری و بی‌اعتنایی به بزرگی حروف) فرق داشته باشد؛ «تخصیص جدید» یعنی مقدار اولیه خالی است و «تثبیت‌نشده» معیار جداگانه‌ای است. این تطبیق اسمی، ادعای تأیید هویت اشخاص در دنیای واقعی نیست.

بخش‌های قدیمی توضیح‌دهندهٔ اسکریپت خط فرمان در ادامه، قرارداد فعلی خروجی برنامهٔ دسکتاپ را تعریف نمی‌کنند.

## 📋 پیش‌نیازها

برای اجرای این پروژه، به محیط پایتون (نسخه ۳.۶ یا بالاتر) و کتابخانه `openpyxl` نیاز دارید.

### نصب وابستگی‌ها
کتابخانه مورد نیاز را با استفاده از دستور زیر نصب کنید:
```bash
pip install openpyxl
```
*(توجه: کتابخانه‌های `csv`, `math` و `collections` جزو کتابخانه‌های استاندارد پایتون هستند و نیاز به نصب جداگانه ندارند.)*

## 📂 ساختار فایل‌های ورودی

اسکریپت برای اجرا به دو فایل CSV با فرمت جداکننده سمی‌کالن (`;`) و انکدینگ `utf-8-sig` نیاز دارد:

1. **`Book1.csv`**: حاوی لیست پشتیبان‌ها و مدیران آن‌ها.
   - ستون‌های مورد نیاز: `نام پشتیبان`, `نام مدیر`
2. **`Book2.csv`**: حاوی لیست دانش‌آموزان و ترجیحات اولیه آن‌ها.
   - ستون‌های مورد نیاز: `شمارنده`, `نام`, `نام خانوادگی`, `نام گروه`, `مدیر`, `پشتیبان`

> **نکته:** نام ستون‌ها در فایل‌های CSV باید دقیقاً مطابق با موارد فوق باشد (سیستم به طور خودکار نرمال‌سازی را انجام می‌دهد، اما کلیدهای اصلی باید یکسان باشند).

## 🚀 نحوه استفاده

1. فایل‌های `Book1.csv` و `Book2.csv` را در همان دایرکتوری که اسکریپت پایتون قرار دارد، ذخیره کنید.
2. اسکریپت را از طریق ترمینال یا خط فرمان اجرا کنید:
   ```bash
   python script.py
   ```
   *(نام فایل اسکریپت خود را جایگزین `script.py` کنید)*
3. پس از اجرای موفقیت‌آمیز، پیام تأیید در کنسول نمایش داده شده و فایل خروجی تولید می‌شود.

## 📤 خروجی‌ها

پس از اجرای برنامه، یک فایل با نام **`final_assignment.xlsx`** در دایرکتوری جاری ایجاد می‌شود که شامل دو شیت است:

1. **جدول نهایی دانش‌آموزان**: لیست کامل دانش‌آموزان به همراه اطلاعات هویتی، پشتیبان اولیه، پشتیبان نهایی تخصیص‌یافته و مدیر پشتیبان نهایی.
2. **گزارش آماری**: خلاصه‌ای از متریک‌های کلیدی فرآیند تخصیص، شامل:
   - تعداد کل دانش‌آموزان و پشتیبان‌ها
   - ظرفیت محاسبه‌شده برای هر پشتیبان
   - حداقل و حداکثر تعداد دانش‌آموز تخصیص‌یافته به یک پشتیبان
   - تعداد دانش‌آموزان تثبیت‌شده، تثبیت‌نشده، تخصیص جدید و تغییر واقعی پشتیبان

## ⚙️ منطق الگوریتم تخصیص

1. **بارگذاری و نرمال‌سازی**: داده‌ها از فایل‌های CSV خوانده و کلیدها و مقادیر آن‌ها برای جلوگیری از خطاهای تطبیق، نرمال‌سازی می‌شوند.
2. **تخصیص اولیه (تثبیت)**: اگر تعداد دانش‌آموزانی که یک پشتیبان را به عنوان ترجیح اول انتخاب کرده‌اند کمتر یا مساوی ظرفیت باشد، همه آن‌ها تثبیت می‌شوند. در غیر این صورت، به تعداد ظرفیت، دانش‌آموزان تثبیت شده و مابقی به «استخر» (Pool) منتقل می‌شوند.
3. **توزیع چرخشی (Round Robin)**: برای دانش‌آموزان موجود در استخر، سیستم به صورت چرخشی بین لیست پشتیبان‌ها حرکت می‌کند. به محض یافتن پشتیبانی با ظرفیت خالی (`remaining_cap > 0`)، دانش‌آموز به او تخصیص می‌یابد و نشانگر به پشتیبان بعدی منتقل می‌شود تا توزیع کاملاً عادلانه باشد.
4. **اعتبارسنجی نهایی**: قبل از تولید خروجی، سه شرط اصلی (برابری تعداد کل، رعایت سقف ظرفیت، و عدم تغییر تخصیص‌های تثبیت‌شده) بررسی می‌شوند. در صورت نقض هر یک، برنامه با خطا (`RuntimeError` یا `AssertionError`) متوقف می‌شود.

## 👤 نویسنده و نگهداری

- **توسعه‌دهنده**: رضا (Reza)
- در صورت بروز هرگونه مشکل یا نیاز به توسعه ویژگی‌های جدید، لطفاً از طریق بخش Issues مخزن اقدام نمایید.

## 📄 مجوز (License)

این پروژه تحت مجوز [MIT License](LICENSE) ارائه شده است (در صورت تمایل می‌توانید فایل LICENSE را به مخزن اضافه کنید).

---

بله، حتماً. در ادامه، نسخه انگلیسی فایل `README.md` با همان ساختار استاندارد، لحن رسمی و رعایت اصول مستندسازی نرم‌افزار ارائه شده است. این نسخه برای قرارگیری در مخازن بین‌المللی (مانند GitHub یا GitLab) کاملاً مناسب است.

---

# Student-Mentor Fair Assignment System

This project is a Python script designed to automate and optimize the assignment of students to mentors. By considering initial preferences, strict capacity limits, and employing a Round Robin algorithm for the equitable distribution of remaining capacities, the system ensures a fair, transparent, and error-free allocation process.

## ✨ Key Features

- **Intelligent Text Normalization**: Automatically resolves Persian/Arabic character discrepancies (e.g., converting Arabic 'ي' to Persian 'ی', 'ك' to 'ک', and trailing 'ة' to 'ه') and removes extra whitespace to ensure accurate data matching.
- **Dynamic Capacity Management**: Automatically calculates the maximum capacity per mentor using the formula `ceil(Total Students / Total Mentors)`.
- **Stabilization & Pooling**: Preserves initial student-mentor assignments up to the mentor's capacity limit. Any excess students are moved to a "Pool" for secondary distribution.
- **Round Robin Fair Distribution**: Equitably and cyclically distributes students from the Pool among mentors who still have available capacity, preventing any single mentor from being disproportionately burdened.
- **Strict Data Validation**: Automatically verifies the integrity of the assignment (total count equality, strict adherence to capacity limits, and guarantee that stabilized students are not reassigned).
- **Structured Excel Output**: Generates a comprehensive Excel file containing both the "Final Student Assignment Table" and a "Statistical Report" for complete process transparency.

## 📋 Prerequisites

To run this project, you need a Python environment (version 3.6 or higher) and the `openpyxl` library.

### Installing Dependencies
Install the required library using the following command:
```bash
pip install openpyxl
```
*(Note: The `csv`, `math`, and `collections` modules are part of the Python Standard Library and do not require separate installation.)*

## 📂 Input File Structure

The script requires two CSV files formatted with a semicolon (`;`) delimiter and `utf-8-sig` encoding:

1. **`Book1.csv`**: Contains the list of mentors and their respective managers.
   - Required columns: `نام پشتیبان` (Mentor Name), `نام مدیر` (Manager Name)
2. **`Book2.csv`**: Contains the list of students and their initial preferences.
   - Required columns: `شمارنده` (Counter/ID), `نام` (First Name), `نام خانوادگی` (Last Name), `نام گروه` (Group Name), `مدیر` (Manager), `پشتیبان` (Initial Mentor)

> **Note:** The column headers in the CSV files must exactly match the Persian terms listed above. The system automatically normalizes the values, but the base keys must remain consistent.

## 🚀 Usage Instructions

1. Place the `Book1.csv` and `Book2.csv` files in the same directory as the Python script.
2. Execute the script via terminal or command prompt:
   ```bash
   python script.py
   ```
   *(Replace `script.py` with the actual name of your Python file.)*
3. Upon successful execution, a confirmation message will be displayed in the console, and the output file will be generated.

## 📤 Outputs

After execution, a file named **`final_assignment.xlsx`** will be created in the current directory. It contains two sheets:

1. **Final Student Table**: A complete list of students, including their identification details, initial mentor, final assigned mentor, and the final mentor's manager.
2. **Statistical Report**: A summary of key allocation metrics, including:
   - Total number of students and mentors
   - Calculated capacity per mentor
   - Minimum and maximum number of students assigned to any single mentor
   - Number of stabilized students (unchanged) and students reassigned from the Pool

## ⚙️ Algorithm Logic

1. **Loading & Normalization**: Data is read from the CSV files, and all keys and values are normalized to prevent matching errors.
2. **Initial Mapping (Stabilization)**: If the number of students who selected a mentor as their first choice is less than or equal to the capacity, all are stabilized. If it exceeds the capacity, students are stabilized up to the limit, and the remainder are moved to the "Pool".
3. **Round Robin Distribution**: For students in the Pool, the system iterates cyclically through the mentor list. Upon finding a mentor with available capacity (`remaining_cap > 0`), the student is assigned to them, and the pointer advances to the next mentor to ensure perfectly fair distribution.
4. **Final Validation**: Before generating the output, three core conditions are verified: total assigned count equals total students, no mentor exceeds their capacity, and no stabilized student has been reassigned. If any condition fails, the program halts with a `RuntimeError` or `AssertionError`.

## 👤 Author & Maintenance

- **Developer**: Reza
- For any issues, bug reports, or feature requests, please open an Issue in the repository.

## 📄 License

This project is licensed under the [MIT License](LICENSE). *(You may add a LICENSE file to the repository if desired).*
