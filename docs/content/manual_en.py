"""Contents of 'user-manual.pdf' (English)."""

from reportlab.platypus import PageBreak

from _pdf_common import bullet_list, h1, h2, h3, image, note, p, table

TITLE = "Duplicate Finder"
SUBTITLE = "User manual"
SHORT_TITLE = "User manual"
COVER_SUMMARY = (
    "A guide to finding duplicate files, grouping similar photos and gathering scattered "
    "images — without the risk of losing anything, because the application never deletes "
    "your originals and everything can be undone.")


def body():
    C = []

    # ======================================================================
    C += [h1("1. What this application does")]
    C += [p(
        "This manual explains how to use <b>Duplicate Finder</b>, the application I "
        "built to tidy up my files, mostly my photos, and which can now help you too. "
        "It has three functions, one per tab:")]
    C += [table([
        ["Tab", "What it is for"],
        ["Exact duplicates",
         "Finds files that are identical byte for byte (the same photo or document "
         "saved several times) and lets you keep just one copy."],
        ["Similar photos",
         "Finds the same photo saved several times even when it is not identical: "
         "recompressed, at a lower resolution or with a colour filter."],
        ["Gather images",
         "Puts all the photos you have scattered across a folder and its subfolders "
         "into a single folder."],
    ], widths_cm=[3.6, 12.0])]
    C += [note(
        "The golden rule I set myself: <b>the application never deletes or modifies your "
        "original files</b>. It only reads them and, when you confirm, <i>moves</i> them "
        "to another folder. Any operation can also be undone from the “History”.")]

    # ======================================================================
    C += [h1("2. Installation and first start")]
    C += [bullet_list([
        "There is nothing to install. Download "
        "<font face='Courier'>Buscador-de-duplicados.exe</font> "
        "(a single file: copy it wherever you like and double-click it) or, if your "
        "antivirus blocks it or takes long, "
        "<font face='Courier'>Buscador-de-duplicados-portable.zip</font>: "
        "unzip it into a folder with a short path (for example "
        r"<font face='Courier'>C:\Apps</font>) and open the .exe inside.",
        "It needs no internet connection and no administrator rights.",
        "The first time it starts in <b>Simple view</b>. The view you choose is "
        "remembered for next time.",
        "The interface is in English or Spanish. It follows the language of Windows, and "
        "the <b>Language</b> selector in the header changes it (it applies the next time "
        "you open the app).",
    ])]
    C += [p(
        "Windows may show an “unknown publisher” warning the first time (because the "
        "executable is not signed). That is normal for small programs; click “More info” "
        "and “Run anyway”.")]

    # ======================================================================
    C += [h1("3. The main window")]
    C += image("01_simple.png", caption=(
        "Simple view, “Exact duplicates” tab, after a scan."))
    C += [p(
        "At the top right there are three settings:")]
    C += [bullet_list([
        "<b>Theme</b>: <i>Automatic</i> (follows the Windows theme), <i>Light</i> or "
        "<i>Dark</i>. It applies immediately and is remembered for next time.",
        "<b>Language</b>: English or Spanish (applies the next time you open the app).",
        "<b>View — Simple / Advanced</b>:",
    ])]
    C += [bullet_list([
        "<b>Simple</b>: the minimum — choose a folder, scan and move. The application "
        "decides by itself which copy to keep in each group.",
        "<b>Advanced</b>: everything appears — scan filters, preferred folder, export to "
        "CSV, the sensitivity slider, and the “History” button.",
    ])]
    C += [p(
        "Right below are the three tabs. Switching tabs does not lose what you have in "
        "the others.")]
    C += [note(
        "Disabled buttons look dull grey (not red or green): it means that action is not "
        "available yet, not that there is an error.")]

    # ======================================================================
    C += [PageBreak(), h1("4. The “Exact duplicates” tab")]

    C += [h2("4.1. Basic use (Simple view)")]
    C += [bullet_list([
        "<b>1.</b> Click “Choose” and select the folder you want to review (for "
        "example your photos folder or a whole disk).",
        "<b>2.</b> Click “Scan”. The progress bar shows two stages: first it checks "
        "sizes, then it computes fingerprints.",
        "<b>3.</b> When it finishes you see the groups of duplicates. The application has "
        "already marked in each group the <b>main copy</b> to keep (the one with the "
        "least “copy-like” name, in the least nested and oldest folder) and the rest to "
        "move.",
        "<b>4.</b> Review. If you want to keep another copy in a group, "
        "<b>double-click</b> its row.",
        "<b>5.</b> Click “Move to quarantine”, choose a folder (it must be <b>outside</b> "
        "the one you scanned) and confirm.",
    ])]
    C += [p(
        "The statistics panel shows how many groups there are, how many duplicate files, "
        "how many would be moved and how much space you would recover.")]

    C += [h2("4.2. Preview and full-size view")]
    C += [p(
        "When you select a file in the list, its preview appears on the right (the image, "
        "or a box with the extension if it is not an image) with its name, path, size, "
        "date and resolution. <b>Click the preview</b> to open the image almost full "
        "screen, with zoom (mouse wheel or buttons) and panning by dragging.")]
    C += image("08_viewer.png", width_cm=13.5, caption=(
        "The image viewer: wheel to zoom, drag to move, “Fit” to fit it in the window."))

    C += [PageBreak(), h2("4.3. Scan options (Advanced view)")]
    C += image("03_options.png", caption=(
        "The “Scan options” panel expanded, with “Images” ticked."))
    C += [h3("Search only these file types")]
    C += [p(
        "Tick one or more categories (Images, Audio, Video, Documents, Archives) and the "
        "extensions field fills itself in. You can also type extensions by hand. If you "
        "leave it empty, duplicates of any type are searched.")]
    C += [h3("Also ignore")]
    C += [p(
        "Discards junk before scanning: extensions "
        "(<font face='Courier'>tmp</font>, <font face='Courier'>log</font>...), "
        "folders (<font face='Courier'>node_modules</font>, "
        "<font face='Courier'>$RECYCLE.BIN</font>...), names "
        "(<font face='Courier'>Thumbs.db</font>...) and 0-byte files. It comes with "
        "reasonable values. What is ignored is not even read, so the scan is faster.")]

    C += [h2("4.4. Choosing what to keep (Advanced view)")]
    C += image("02_advanced.png", caption=(
        "Advanced view: “Preferred folder”, “Rule by folder”, “Choose the main one”, "
        "“View file types” and “Export CSV” come back."))
    C += [bullet_list([
        "<b>Preferred folder + “Rule by folder”</b>: enter a folder "
        "(for example <font face='Courier'>D:\\Photos\\Organized</font>) and click the "
        "button. In each group, if there is a copy inside that folder, that one is kept. "
        "Groups without any copy there are highlighted so you decide by hand.",
        "<b>“Choose the main one”</b>: applies the same automatic preselection as the "
        "Simple view.",
        "<b>Working with the table</b>: one click selects (and shows the preview); a click "
        "on the “Decision” column toggles keep/move for that file; a double-click leaves "
        "that copy as the only one to keep.",
        "<b>“View file types”</b>: shows the duplicates grouped by extension with their "
        "weight, to decide what to add to the filter.",
        "<b>“Export CSV”</b>: saves the full report to a file.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("5. The “Similar photos” tab")]
    C += image("04_similar.png", caption=(
        "Each group shows the similar photos with their thumbnail, resolution, size and "
        "percentage of similarity."))
    C += [bullet_list([
        "<b>1.</b> Choose the folder and click “Analyze”.",
        "<b>2.</b> The <b>Sensitivity</b> slider (Advanced view) controls how alike two "
        "photos must be to count as the same group: “strict” groups fewer, “tolerant” "
        "groups more.",
        "<b>3.</b> In each group, the first photo is the <b>best quality</b> (highest "
        "resolution) and it is marked to keep. If you prefer another one, click “Keep "
        "this one” below it.",
        "<b>4.</b> Click a thumbnail to see the photo large and compare.",
        "<b>5.</b> If there are many groups they are split into pages: use “Previous” and "
        "“Next” under the list. What you decide on each page is kept.",
        "<b>6.</b> “Move to quarantine” moves the unmarked photos from <b>all</b> the "
        "pages.",
    ])]
    C += [h2("5.1. What it finds and what it does not")]
    C += [table([
        ["It finds", "It does not find"],
        ["The same photo recompressed or at lower quality", "Cropped photos"],
        ["The same photo resized (smaller)", "Rotated or flipped photos"],
        ["The same photo with a colour or brightness filter", "A piece of a collage"],
        ["The same photo with a watermark in a corner", ""],
    ], widths_cm=[8.0, 7.6])]

    # ======================================================================
    C += [PageBreak(), h1("6. The “Gather images” tab")]
    C += image("05_gather.png", caption=(
        "List of the images found, with a checkbox to exclude any of them."))
    C += [bullet_list([
        "<b>1.</b> Choose the folder to review. The "
        "<b>“All subfolders” / “First level only”</b> selector decides whether it "
        "searches in depth or only what sits loose in the folder.",
        "<b>2.</b> Click “Find images”. They appear with their thumbnail; untick the ones "
        "you do not want to take.",
        "<b>3.</b> Choose the <b>common destination folder</b>.",
        "<b>4.</b> (Advanced view) Choose <b>Move</b> (removes them from the source) or "
        "<b>Copy</b> (keeps the originals), and the strategy:",
    ])]
    C += [table([
        ["Strategy", "What it does"],
        ["By files",
         "Each image goes to destination/<i>same subfolder</i>. For example "
         "“holidays/beach.jpg” ends up in “destination/holidays/beach.jpg”."],
        ["Whole folder",
         "Moves or copies the folder you are reviewing in full (with everything inside "
         "it) to “destination/FolderName/”."],
    ], widths_cm=[3.4, 12.2])]

    C += [h2("6.1. Files that are not images")]
    C += [p(
        "If those folders also hold documents, music, etc., and you use the “By files” "
        "strategy, this dialog appears:")]
    C += image("06_types.png", width_cm=12.5, caption=(
        "For each file type you choose what to do."))
    C += [bullet_list([
        "<b>Leave</b>: it is not moved, it stays where it is.",
        "<b>Move</b>: it goes to the destination with its same subfolder, like the "
        "images.",
        "<b>Group</b>: all the files of that type go to a folder with the name you type "
        "(for example “Documents”), keeping the subfolders inside.",
    ])]

    # ======================================================================
    C += [PageBreak(), h1("7. History and undo")]
    C += [p(
        "In <b>Advanced view</b>, the <b>“History”</b> button in the header opens this "
        "window from any tab:")]
    C += image("07_history.png", width_cm=13.5, caption=(
        "Every move or copy operation is recorded, with its “Undo” button."))
    C += [bullet_list([
        "If the operation was a <b>move</b>, “Undo” puts every file back in its original "
        "location. If something already exists at that path, it warns you and overwrites "
        "nothing.",
        "If the operation was a <b>copy</b>, “Undo” deletes the copies in the destination "
        "(with a clear confirmation). It is the only case in which the application "
        "deletes anything, and only files it created itself.",
    ])]
    C += [p(
        "The history is saved in "
        "<font face='Courier'>%APPDATA%\\BuscadorDuplicados\\history.json</font> "
        "and keeps the latest operations.")]

    # ======================================================================
    C += [h1("8. The quarantine folder and the logs")]
    C += [bullet_list([
        "You choose the quarantine folder (or the destination folder, in “Gather "
        "images”) every time. There is no fixed one.",
        "Inside it the subfolder structure of the source is recreated, so you know where "
        "each file came from.",
        "A CSV is written "
        "(<font face='Courier'>_log_quarantine_DATE.csv</font> or "
        "<font face='Courier'>_log_gather_DATE.csv</font>) with the source and "
        "destination of each file, in case you prefer to review or undo by hand.",
        "Nothing is deleted: review that folder at your leisure and delete yourself "
        "whatever you no longer need.",
    ])]

    # ======================================================================
    C += [h1("9. Tips and frequently asked questions")]
    C += [table([
        ["Question", "Answer"],
        ["Can it delete my photos by accident?",
         "Not your originals. It only moves files, and always after a confirmation. "
         "Everything can be undone from the History. The only time it deletes anything "
         "is when you undo a copy: it removes the copies it created itself, and asks for "
         "confirmation first."],
        ["I got an “unexpected error” notice. What do I do?",
         r"The application writes what happened to a text file: "
         r"<font face='Courier'>%APPDATA%\BuscadorDuplicados\logs\app.log</font> "
         "(paste that path into Explorer and open it with Notepad). You can keep using "
         "the application, and your files have not been touched. If the failure repeats, "
         "close and reopen it; if you want to report the problem, attach that file."],
        ["I moved things and I see empty folders at the source.",
         "That is normal: the files inside were moved, not the folders. The empty folder "
         "stays; you can delete it yourself if you want."],
        ["The scan takes very long.",
         "Use the “Search only these file types” filter (for example Images) or narrow "
         "the folder. The first pass (sizes) is fast; the time goes into computing "
         "fingerprints of large files."],
        ["What is the difference between the first two tabs?",
         "“Exact duplicates” looks for identical files; “Similar photos” looks for the "
         "same photo even if it was re-saved with another quality or filter."],
        ["Can it be used on an external or network drive?",
         "Yes. Keep in mind that moving between different drives is slower (it copies "
         "and then deletes the original)."],
    ], widths_cm=[5.4, 10.2])]

    return C
