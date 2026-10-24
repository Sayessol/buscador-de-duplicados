"""English texts (the default language). Same keys and placeholders as es.py."""

MESSAGES = {
    # breakdown
    "breakdown.exclude": "Exclude",
    "breakdown.intro": (
        "Sorted by space used. “Exclude” adds the extension to the filter; you "
        "then need to scan again."
    ),
    "breakdown.row_detail": "  {count} files   ·   {size}",
    "breakdown.title": "File types among the duplicates",
    "breakdown.title_added": "File types  ·  .{ext} added to the filter",

    # category
    "category.archives": "Archives",
    "category.audio": "Audio",
    "category.documents": "Documents",
    "category.images": "Images",
    "category.video": "Video",

    # common
    "common.all_files": "All files",
    "common.app_name": "Duplicate Finder",
    "common.cancel": "Cancel",
    "common.cancelling": "Cancelling…",
    "common.choose": "Choose",
    "common.close": "Close",
    "common.confirm": "Confirm",
    "common.confirm_title": "Confirm move to quarantine",
    "common.continue_question": "\n\nContinue?",
    "common.copying": "Copying",
    "common.date_format": "%Y-%m-%d %H:%M",
    "common.done": "Done.",
    "common.done_title": "Done",
    "common.error_detail": "{name}: {datum}",
    "common.file_gone": "the file is no longer where it was",
    "common.folder_placeholder": "e.g.  D:\\Photos",
    "common.invalid_folder_title": "Invalid folder",
    "common.invalid_quarantine_title": "Invalid quarantine folder",
    "common.log_note": "\n\nLog: {log_path}",
    "common.move_error_title": "Error while moving",
    "common.move_quarantine": "Move to quarantine",
    "common.moving": "Moving",
    "common.no_extension": "(no extension)",
    "common.not_a_folder": "Not a folder: {root_folder}",
    "common.pick_quarantine": "Choose (or create) the quarantine folder",
    "common.scan": "Scan",
    "common.tile_recoverable": "Recoverable space",
    "common.warning": "Warning",

    # csv
    "csv.action": "Action",
    "csv.date": "Date",
    "csv.destination": "Destination",
    "csv.duplicate_group": "Duplicate_Group",
    "csv.error": "Error",
    "csv.full_path": "Full_Path",
    "csv.group": "Group",
    "csv.hash": "Hash",
    "csv.scanned_folder": "Scanned_Folder",
    "csv.size": "Size",
    "csv.size_bytes": "Size_Bytes",
    "csv.source": "Source",
    "csv.source_root": "Source_Root",
    "csv.status": "Status",
    "csv.status_done": "done",
    "csv.status_error": "ERROR",
    "csv.status_moved": "moved",

    # exact
    "exact.all_kinds_placeholder": "empty = all file types are searched",
    "exact.cancelled": "Scan cancelled.",
    "exact.cancelled_detail": "Press “Scan” to try again.",
    "exact.cancelled_title": "Scan cancelled",
    "exact.categories_hint": (
        "Tick a category or type extensions by hand. If you leave it empty, "
        "duplicates of any file type are searched."
    ),
    "exact.choose_folder_header": "Choose the folder you want to review",
    "exact.choose_main": "Choose the main one",
    "exact.clear_all": "Clear all",
    "exact.click_to_enlarge": "Click to see the image larger",
    "exact.confirm_msg": (
        "{n} file(s) ({frees}) will be MOVED to:\n\n{quarantine_folder}\n\nThe "
        "originals you marked to keep are NOT touched. Nothing is deleted: "
        "everything stays in quarantine for you to review and delete manually "
        "whenever you want.\n\nMove now?"
    ),
    "exact.defaults": "Default values",
    "exact.empty_detail": (
        "Choose a folder above and press “Scan”. The groups of duplicate files "
        "will appear here."
    ),
    "exact.empty_title": "No results yet",
    "exact.error_msg": "A problem has occurred:\n\n{name}: {e}",
    "exact.error_title": "Error during the scan",
    "exact.excluded_suffix": "  ·  {total_excluded} ignored by the filter",
    "exact.export_csv": "Export CSV",
    "exact.extensions": "Extensions:",
    "exact.failed": "The scan has failed.",
    "exact.failed_note": "\n{failed} could not be moved (see the log CSV).",
    "exact.folders": "Folders:",
    "exact.hint_all_resolved": (
        "Every group has exactly one copy marked to keep. You can now move to "
        "quarantine."
    ),
    "exact.hint_main_kept": (
        "The app will keep the main copy of each group. Double-click a row to "
        "keep another one. When you are ready, press “Move to quarantine”."
    ),
    "exact.hint_unresolved": (
        "{count} group(s) unresolved (highlighted in the table). Mark exactly "
        "one copy to keep in each. The “Move to quarantine” button is locked."
    ),
    "exact.ignore_also": "Also ignore:",
    "exact.ignore_empty": "Ignore 0-byte files",
    "exact.invalid_folder_msg": "The path does not exist or is not a folder:\n\n{folder}",
    "exact.keep_header": "Decide which copy to keep in each group",
    "exact.missing_folder_msg": "Choose a folder to scan first.",
    "exact.missing_folder_title": "Folder missing",
    "exact.move_done": "Move to quarantine finished.",
    "exact.move_failed": "The move has failed.",
    "exact.moved_summary": "{moved} file(s) moved ({size}).",
    "exact.moved_title": "Files moved to quarantine",
    "exact.moved_totals": (
        "{moved} file(s) moved to quarantine. Scan again if you want to "
        "continue."
    ),
    "exact.moving": "Moving to quarantine…",
    "exact.names": "Names:",
    "exact.need_preferred_msg": "Type or choose a preferred folder first.",
    "exact.need_preferred_title": "Preferred folder missing",
    "exact.no_preview": "(no preview)",
    "exact.no_such_folder_msg": (
        "The preferred folder does not exist right "
        "now:\n\n{preferred_folder}\n\nDo you want to apply the rule anyway? "
        "(groups without a match will stay undecided)"
    ),
    "exact.no_such_folder_title": "The folder does not exist",
    "exact.none_found": "No duplicates were found.",
    "exact.none_found_detail": "{total_files} files were reviewed and all of them are unique.",
    "exact.none_found_title": "No duplicates found",
    "exact.not_scanned": "Not scanned yet.",
    "exact.only_kinds": "Search only these file types:",
    "exact.open_quarantine_question": "\n\nDo you want to open the quarantine folder?",
    "exact.options_toggle": "Scan options (filter by file type)",
    "exact.pick_preferred_folder": "Choose the preferred folder",
    "exact.pick_scan_folder": "Choose the folder to scan",
    "exact.preferred_folder": "Preferred folder:",
    "exact.preferred_placeholder": (
        "Copies inside this folder are kept.  e.g.  D:\\Photos\\Organized"
    ),
    "exact.preparing": "Preparing the scan…",
    "exact.preview_hint": "Select a file\nto see the preview",
    "exact.report_saved_msg": "{n} duplicate groups were saved to:\n\n{path}",
    "exact.report_saved_title": "Report saved",
    "exact.rule_applied": "Rule applied: {resolved} group(s) resolved automatically.",
    "exact.rule_by_folder": "Rule by folder",
    "exact.rule_no_match": (
        "\n{no_match} group(s) have no copy inside the preferred folder: they "
        "are highlighted so you can choose manually (one click on the copy you "
        "want to keep, or double-click to keep only that one)."
    ),
    "exact.rule_title": "Automatic rule",
    "exact.save_failed_msg": "Could not write the file:\n\n{e}",
    "exact.save_failed_title": "Could not save",
    "exact.save_report_title": "Save CSV report",
    "exact.scan_again": " Scan again to continue.",
    "exact.scanning": "Scanning…",
    "exact.searching_detail": "Looking for duplicate files.",
    "exact.separate_hint": "Separate the values with spaces or commas.",
    "exact.tile_files": "Duplicate files",
    "exact.tile_groups": "Duplicate groups",
    "exact.tile_to_move": "Files to move",
    "exact.totals": "{total_groups} groups · {total_files_duplicates} duplicate files{excl_text}",
    "exact.totals_none": "{total_files} files reviewed{excl_text} · 0 duplicates.",
    "exact.unreadable": "  {count} file(s) could not be read.",
    "exact.view_kinds": "View file types",

    # gather
    "gather.action_copy": "Copy",
    "gather.action_label": "Action:",
    "gather.action_move": "Move",
    "gather.and_more": "… and {hidden} more (all the marked ones will be gathered anyway).",
    "gather.confirm_and_others": " and {n_others} more file(s)",
    "gather.confirm_files": "You are about to {upper} {count} image(s)",
    "gather.confirm_tail": " to:\n\n{destination}\n\nSubfolders are kept. Continue?",
    "gather.confirm_whole_folder": (
        "You are about to {upper} the folder “{name}” in its ENTIRETY (with "
        "everything inside it) to:\n\n{destination}\\{name}\\\n\nContinue?"
    ),
    "gather.description_files": "{count} images",
    "gather.description_folder": "folder “{name}” (whole)",
    "gather.destination_placeholder": "Common destination folder",
    "gather.done_summary": "Done: {count} file(s) {verb}.",
    "gather.empty_detail": (
        "Choose a folder and press “Find images”. They will appear here so you "
        "can choose which ones to gather."
    ),
    "gather.error_detail": "{name}: {e}",
    "gather.error_title": "Error while gathering",
    "gather.failed": "The operation has failed.",
    "gather.failed_suffix": "  {count} with errors.",
    "gather.find_images": "Find images",
    "gather.first_level_suffix": " at the first level",
    "gather.folder_placeholder": "Folder to review.  e.g.  D:\\Photos",
    "gather.folder_progress": "{verb} folder “{name}”…",
    "gather.gather_here": "Gather here",
    "gather.header": "Gather all the images into one folder",
    "gather.infinitive_copy": "copy",
    "gather.infinitive_move": "move",
    "gather.intro": (
        "Puts the photos scattered across a folder and its subfolders in a "
        "single place."
    ),
    "gather.invalid_destination_title": "Invalid destination",
    "gather.invalid_folder_msg": "Choose a folder to review.",
    "gather.missing_destination_msg": "Choose the common destination folder.",
    "gather.missing_destination_title": "Destination missing",
    "gather.no_images_detail": "There are no image files in that folder",
    "gather.no_images_title": "No images found",
    "gather.not_searched_title": "Not searched yet",
    "gather.open_destination_question": "\n\nOpen the destination folder?",
    "gather.past_copy": "copied",
    "gather.past_move": "moved",
    "gather.pick_destination": "Choose (or create) the destination folder",
    "gather.pick_folder": "Choose the folder to review",
    "gather.read_error_title": "Error reading the folder",
    "gather.result_detail": "{count} file(s) {verb} to:\n\n{destination}",
    "gather.result_title": "{count} file(s) {verb}",
    "gather.scope_all": "All subfolders",
    "gather.scope_first": "First level only",
    "gather.starting": "Starting…",
    "gather.strategy_files": "By files",
    "gather.strategy_folder": "Whole folder",
    "gather.strategy_label": "Strategy:",
    "gather.tile_found": "Images found",
    "gather.tile_marked": "Marked to gather",
    "gather.tile_others": "Other files",
    "gather.totals": "{n} image(s) marked · {others} files that are not images",
    "gather.totals_done": "{count} file(s) {verb} to {destination}.",
    "gather.undo_hint": (
        "You can undo it from “History” (above, in Advanced view). Search "
        "again if you want to continue."
    ),

    # history
    "history.already_undone": "this operation was already undone",
    "history.gone_from_destination": "it is no longer in the destination",
    "history.op_not_found": "operation not found",
    "history.original_path_taken": "something already exists at the original path",
    "history.description_exact": "{count} exact duplicates",
    "history.description_similar": "{count} similar photos",

    # history_ui
    "history_ui.confirm_delete_copies": (
        "{n} copied file(s) in:\n\n{destination}\n\nwill be DELETED. These are "
        "the copies the app made. The originals are not touched. This cannot "
        "be undone.\n\nContinue?"
    ),
    "history_ui.confirm_return": (
        "{n} file(s) will be returned to their original location (from "
        "{destination}).\n\nContinue?"
    ),
    "history_ui.empty": "No operations recorded yet.",
    "history_ui.failure_line": "· {name}: {m}",
    "history_ui.intro": (
        "Every operation can be undone. “Move” puts the files back in place; "
        "“copy” deletes the copies in the destination."
    ),
    "history_ui.item_title": "·  {n} file(s) {verb}",
    "history_ui.kind_gather": "Gather images",
    "history_ui.kind_gather_folder": "Gather (whole folder)",
    "history_ui.refresh": "Refresh",
    "history_ui.title": "Operation history",
    "history_ui.undo": "Undo",
    "history_ui.undo_done": "Operation undone: {reverted} file(s).",
    "history_ui.undo_title": "Undo operation",
    "history_ui.undo_warnings_msg": (
        "Reverted: {reverted}.\n{count} could not be reverted:\n\n{detail}"
    ),
    "history_ui.undo_warnings_title": "Undo with warnings",
    "history_ui.undone": "{OK} undone",
    "history_ui.verb_copied": "copied",
    "history_ui.verb_moved": "moved",

    # kinds
    "kinds.apply": "Apply",
    "kinds.folder_name_placeholder": "folder name",
    "kinds.group": "Group",
    "kinds.intro": (
        "These folders also contain files that are not images. Choose what to "
        "do with each type:"
    ),
    "kinds.leave": "Leave",
    "kinds.move": "Move",
    "kinds.title": "Files that are not images",

    # main
    "main.error_msg": (
        "An unexpected error has occurred ({name}: {val}).\n\n{where}\n\nYou "
        "can keep using the application; if the failure repeats, close it and "
        "open it again. Your files have not been touched."
    ),
    "main.error_title": "Unexpected error",
    "main.history": "History",
    "main.language_changed_msg": "The language will change the next time you open the app.",
    "main.language_changed_title": "Language",
    "main.language_label": "Language:",
    "main.log_failed": "The log could not be saved.",
    "main.log_saved": "The error has been written to the log:\n{path}",
    "main.mode_advanced": "Advanced",
    "main.mode_simple": "Simple",
    "main.tab_exact": "Exact duplicates",
    "main.tab_gather": "Gather images",
    "main.tab_similar": "Similar photos",
    "main.tagline": (
        "Finds repeated files and moves them to quarantine. Your originals are "
        "never deleted."
    ),
    "main.theme_auto": "Automatic",
    "main.theme_dark": "Dark",
    "main.theme_label": "Theme:",
    "main.theme_light": "Light",
    "main.view_label": "View:",
    "main.window_title": "Duplicate Finder {version}",

    # moves
    "moves.inside_source": (
        "The destination is inside the source folder. Choose a folder outside "
        "it."
    ),
    "moves.progress": "{verb} {i}/{total}: {basename}",
    "moves.same_folder": "The destination cannot be the same folder as the source.",
    "moves.source_inside_destination": (
        "Warning: the source folder is inside the destination. You can "
        "continue, but check that this is what you want."
    ),

    # perceptual
    "perceptual.analyzing": "Analyzing images… ({i}/{total})",
    "perceptual.finished": "Comparison finished.",

    # quarantine
    "quarantine.inside_scanned": (
        "The quarantine folder is inside the scanned folder. Choose a folder "
        "outside it."
    ),
    "quarantine.progress": "Moving {i}/{total}: {basename}",
    "quarantine.same_as_scanned": "The quarantine folder cannot be the same as the scanned folder.",
    "quarantine.scanned_inside_quarantine": (
        "Warning: the scanned folder is inside the quarantine folder. You can "
        "continue, but check that this is what you want."
    ),
    "quarantine.unresolved_groups": (
        "There are unresolved groups: each group must have exactly one copy "
        "marked to keep before moving."
    ),

    # report
    "report.group_label": "Group {number}",

    # scan
    "scan.finished": "Scan finished.",
    "scan.step_hashes": "Step 2/2: computing hashes... ({processed}/{total_candidates})",
    "scan.step_sizes": "Step 1/2: checking sizes... ({total_files} files)",
    "scan.step_verifying": (
        "Step 2/2: verifying whole files... "
        "({full_processed}/{total_finalists})"
    ),

    # similar
    "similar.analyze": "Analyze",
    "similar.analyzing": "Analyzing…",
    "similar.best_quality": "best quality",
    "similar.cancelled": "Analysis cancelled.",
    "similar.cancelled_detail": "Press “Analyze” to try again.",
    "similar.cancelled_title": "Analysis cancelled",
    "similar.comparing_detail": "Comparing the photos with each other.",
    "similar.confirm_msg": (
        "{n} photo(s) ({frees}) will be MOVED to:\n\n{destination}\n\nThe "
        "photos marked to keep are NOT touched. Nothing is deleted.\n\nMove "
        "now?"
    ),
    "similar.empty_detail": (
        "Choose a folder with photos and press “Analyze”. The groups of "
        "similar photos will appear here, with a thumbnail of each."
    ),
    "similar.error_detail": "{name}: {e}",
    "similar.error_title": "Error during the analysis",
    "similar.failed": "The analysis has failed.",
    "similar.finding_images": "Looking for images…",
    "similar.finished": "Analysis finished.{extra}",
    "similar.folder_placeholder": "Folder with photos.  e.g.  D:\\Photos",
    "similar.group_title": "Group {number}   ·   {count} similar photos   ·   frees {size}",
    "similar.header": "Look for similar photos (not identical)",
    "similar.intro": (
        "Finds the same photo saved several times: recompressed, at a lower "
        "resolution or with a colour filter. It does not detect crops or "
        "rotations."
    ),
    "similar.invalid_folder_msg": "Choose a folder with photos to analyze.",
    "similar.keep_this": "Keep this one",
    "similar.kept": "Kept",
    "similar.loading_thumbnails": "Loading thumbnails… ({processed_count}/{total})",
    "similar.moved_detail": "{count} photos were moved. Analyze again to continue.",
    "similar.moved_summary": "{count} photos were moved.",
    "similar.moved_title": "Photos moved to quarantine",
    "similar.moved_totals": (
        "{count} photo(s) moved to quarantine. Analyze again if you want to "
        "continue."
    ),
    "similar.next": "Next  ›",
    "similar.no_preview": "(no\npreview)",
    "similar.none_found": "No similar photos were found.",
    "similar.none_found_detail": (
        "{total_images} images were compared. Try raising the sensitivity if "
        "you expected more."
    ),
    "similar.none_found_title": "No similar photos found",
    "similar.normal": "normal",
    "similar.not_analyzed": "Not analyzed yet.",
    "similar.not_analyzed_title": "Not analyzed yet",
    "similar.open_quarantine_question": "\n\nOpen the quarantine folder?",
    "similar.page_label": "Page {page} of {pages}  ·  groups {first}–{end} of {total}",
    "similar.pick_folder": "Choose the folder with photos",
    "similar.previous": "‹  Previous",
    "similar.ready": "Ready: {to_move} photos will be moved ({size}).",
    "similar.sensitivity": "Sensitivity:",
    "similar.sensitivity_label": "  ({label})",
    "similar.similarity": "{percent:.0f}% similar",
    "similar.strict": "strict",
    "similar.tile_groups": "Similar groups",
    "similar.tile_photos": "Photos in groups",
    "similar.tile_to_move": "Photos to move",
    "similar.tolerant": "tolerant",
    "similar.too_many_kept": (
        "{count} group(s) with more than one photo marked to keep. Leave only "
        "one in each group."
    ),
    "similar.totals_none": "{total_images} images analyzed{extra} · 0 groups.",
    "similar.unreadable_suffix": "  ·  {count} unreadable image(s)",
    "similar.very_strict": "very strict",
    "similar.very_tolerant": "very tolerant",

    # table
    "table.col_decision": "Decision",
    "table.col_group": "Group / File",
    "table.col_size": "Size",
    "table.decision_keep": "✔ keep",
    "table.decision_move": "→ move",
    "table.group_title": "Group {number}  ·  {count} copies",
    "table.reclaim": "frees {size}",
    "table.state_choose": "choose which to keep",
    "table.state_ready": "ready",

    # thumbs
    "thumbs.no_extension": "no ext.",

    # viewer
    "viewer.cannot_show": "This image cannot be shown.",
    "viewer.fit": "Fit",
}
