---
id: d02
register: document
name: Pull request description from a diff
---
Write a pull request description for the following change.

DIFF:
--- a/src/importer/spreadsheet.py
+++ b/src/importer/spreadsheet.py
@@ -18,10 +18,17 @@ def read_rows(path):
     book = open_workbook(path)
     sheet = book.sheet_by_index(0)
-    for i in range(1, sheet.nrows):
-        row = sheet.row_values(i)
-        if not row[0]:
-            break
-        yield row
+    for i in range(1, sheet.nrows):
+        row = sheet.row_values(i)
+        if not any(str(cell).strip() for cell in row):
+            continue
+        yield row

@@ -41,6 +48,9 @@ def import_file(path, account):
     created = 0
     for row in read_rows(path):
-        Contact.objects.create(account=account, **parse(row))
-        created += 1
+        try:
+            Contact.objects.create(account=account, **parse(row))
+            created += 1
+        except ValueError as exc:
+            errors.append((i, str(exc)))
     return created

--- a/tests/test_spreadsheet.py
+++ b/tests/test_spreadsheet.py
@@ -0,0 +1,22 @@
+def test_blank_row_in_middle_does_not_truncate():
+    rows = list(read_rows(fixture("blank-row-middle.xlsx")))
+    assert len(rows) == 40
+
+def test_bad_date_is_reported_not_raised():
+    result = import_file(fixture("bad-date.xlsx"), account)
+    assert result.created == 39
+    assert result.errors == [(12, "could not read date '31/02/2026'")]

Context: customers upload a spreadsheet of contacts. Support had three reports this month of imports that finished successfully but contained fewer contacts than the file. The cause was a blank row partway down the sheet, which stopped the import silently. A single bad date also aborted the whole import with a stack trace shown to the customer.
