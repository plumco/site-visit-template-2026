# ==========================================
# TAB 4: SITE CARD REPORT VIEW
# ==========================================
with tab_site_card:

    st.markdown("### 🏢 Site Card Report")
    st.markdown("Select one site to view complete site master information above and all VisitLog data below with latest comment.")

    # -----------------------------
    # Helper functions for Site Card
    # -----------------------------
    def get_first_col(df, col_list):
        for c in col_list:
            if c in df.columns:
                return c
        return None

    def clean_value(value):
        value = str(value).strip()
        if value.lower() in ["nan", "none", "nat", "", "null"]:
            return "-"
        return value

    def get_unique_values(df, col):
        if df.empty or col not in df.columns:
            return []
        return sorted(
            df[col]
            .astype(str)
            .str.strip()
            .replace(["", "nan", "None", "NaN"], pd.NA)
            .dropna()
            .unique()
            .tolist()
        )

    def site_filter(df, site_col, site_name):
        if df.empty or site_col not in df.columns:
            return pd.DataFrame()

        return df[
            df[site_col]
            .astype(str)
            .str.strip()
            .str.lower()
            == str(site_name).strip().lower()
        ].copy()

    def horizontal_report_table(title, data_dict):
        st.markdown(f"#### {title}")

        report_df = pd.DataFrame([data_dict])
        st.dataframe(
            report_df.astype(str),
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------
    # Detect main columns
    # -----------------------------
    if master_df.empty and visits_df.empty:
        st.warning("No MasterProject or VisitLog data found.")

    else:
        master_site_col = get_first_col(
            master_df,
            [
                "PROJECT",
                "PROJECT NAME",
                "Project",
                "Project Name",
                "Site Name",
                "SITE NAME"
            ]
        )

        visit_site_col = get_first_col(
            visits_df,
            [
                "Site Name",
                "SITE NAME",
                "PROJECT",
                "PROJECT NAME",
                "Project",
                "Project Name"
            ]
        )

        # -----------------------------
        # Create site dropdown list
        # -----------------------------
        site_list = []

        if master_site_col:
            site_list += get_unique_values(master_df, master_site_col)

        if visit_site_col:
            site_list += get_unique_values(visits_df, visit_site_col)

        site_list = sorted(list(set(site_list)))

        if not site_list:
            st.warning("No site name found in MasterProject or VisitLog.")

        else:
            selected_site = st.selectbox(
                "Select Site Name",
                site_list,
                key="site_card_select_site"
            )

            site_master = site_filter(master_df, master_site_col, selected_site) if master_site_col else pd.DataFrame()
            site_visits = site_filter(visits_df, visit_site_col, selected_site) if visit_site_col else pd.DataFrame()

            # -----------------------------
            # Prepare VisitLog columns
            # -----------------------------
            if not site_visits.empty:
                if "Status" not in site_visits.columns:
                    site_visits["Status"] = site_visits.apply(get_visit_status, axis=1)

                if "Date of Visit" in site_visits.columns:
                    site_visits["Date Parsed"] = pd.to_datetime(site_visits["Date of Visit"], errors="coerce")
                    site_visits["Month"] = site_visits["Date Parsed"].dt.strftime("%b %Y")
                    site_visits["Month"] = site_visits["Month"].fillna("Unknown")
                else:
                    site_visits["Month"] = "Unknown"

                floor_col = get_first_col(site_visits, ["FloorsVisited", "Floors Visited", "Floor Visited"])
                if floor_col:
                    site_visits["Num_Floors"] = site_visits[floor_col].apply(parse_floor)
                else:
                    site_visits["Num_Floors"] = 0

            # -----------------------------
            # Master Project main columns
            # -----------------------------
            col_project = master_site_col
            col_state = get_first_col(master_df, ["STATE", "State"])
            col_dist = get_first_col(master_df, ["DISTRICT / CITY", "DISTRICT", "District", "CITY", "City"])
            col_area = get_first_col(master_df, ["Area", "AREA"])
            col_status = get_first_col(master_df, ["STATUS OF PROJECT", "Status", "STATUS"])
            col_ongoing = get_first_col(master_df, ["VISIT ONGOING", "Visit Ongoing"])
            col_tech = get_first_col(master_df, ["Technical Person", "TECHNICAL PERSON NAME", "TECHNICAL PERSON"])
            col_sales = get_first_col(master_df, ["Sells Person", "SALES PERSON NAME", "SALES PERSON", "Sales Person"])
            col_distb = get_first_col(master_df, ["Distributer", "DISTRIBUTOR NANE", "DISTRIBUTOR", "Distributor"])

            if not site_master.empty:
                master_row = site_master.iloc[0]
            else:
                master_row = pd.Series(dtype="object")

            # -----------------------------
            # Latest visit details
            # -----------------------------
            last_visit_date = "-"
            last_visit_by = "-"
            last_comment = "-"

            if not site_visits.empty:
                if "Date Parsed" in site_visits.columns:
                    latest_df = site_visits.sort_values("Date Parsed", ascending=False)
                else:
                    latest_df = site_visits.copy()

                last_row = latest_df.iloc[0]

                if "Date of Visit" in latest_df.columns:
                    last_visit_date = clean_value(last_row.get("Date of Visit", "-"))

                associate_col = get_first_col(latest_df, ["Associate ID", "Associate", "Technical Person"])
                if associate_col:
                    last_visit_by = clean_value(last_row.get(associate_col, "-"))

                if "Comment" in latest_df.columns:
                    last_comment = clean_value(last_row.get("Comment", "-"))

            # -----------------------------
            # KPI Calculation
            # -----------------------------
            total_visit_records = len(site_visits)

            total_floor_visits = 0
            submitted_reports = 0
            pending_reports = 0
            technical_na = 0

            if not site_visits.empty:
                total_floor_visits = int(site_visits["Num_Floors"].sum()) if "Num_Floors" in site_visits.columns else 0
                submitted_reports = len(site_visits[site_visits["Status"] == "Submitted"]) if "Status" in site_visits.columns else 0
                pending_reports = len(site_visits[site_visits["Status"] == "Pending"]) if "Status" in site_visits.columns else 0
                technical_na = len(site_visits[site_visits["Status"] == "Technical (NA)"]) if "Status" in site_visits.columns else 0

            # -----------------------------
            # Site Header Report
            # -----------------------------
            st.markdown("---")
            st.markdown(f"## 🏢 {selected_site}")

            header_data = {
                "Site Name": selected_site,
                "State": clean_value(master_row.get(col_state, "-")) if col_state else "-",
                "District / City": clean_value(master_row.get(col_dist, "-")) if col_dist else "-",
                "Area": clean_value(master_row.get(col_area, "-")) if col_area else "-",
                "Project Status": clean_value(master_row.get(col_status, "-")) if col_status else "-",
                "Visit Ongoing": clean_value(master_row.get(col_ongoing, "-")) if col_ongoing else "-"
            }

            horizontal_report_table("📌 Site Information", header_data)

            team_data = {
                "Technical Person": clean_value(master_row.get(col_tech, "-")) if col_tech else "-",
                "Sales Person": clean_value(master_row.get(col_sales, "-")) if col_sales else "-",
                "Distributor": clean_value(master_row.get(col_distb, "-")) if col_distb else "-",
                "Last Visit Date": last_visit_date,
                "Last Visit By": last_visit_by
            }

            horizontal_report_table("👷 Team / Responsibility Information", team_data)

            # -----------------------------
            # Summary KPI in report format
            # -----------------------------
            st.markdown("#### 📊 Visit Summary")

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric("Total Visit Records", total_visit_records)
            c2.metric("Total Floor Visits", total_floor_visits)
            c3.metric("Submitted Reports", submitted_reports)
            c4.metric("Pending Reports", pending_reports)
            c5.metric("Technical NA", technical_na)

            # -----------------------------
            # Latest Comment
            # -----------------------------
            st.markdown("#### 🕒 Last Comment")

            st.info(last_comment)

            # -----------------------------
            # Full MasterProject data above
            # -----------------------------
            st.markdown("---")
            st.markdown("## 📌 Complete MasterProject Details")

            if site_master.empty:
                st.warning("This site is available in VisitLog, but not found in MasterProject.")
            else:
                st.dataframe(
                    site_master.astype(str),
                    use_container_width=True,
                    hide_index=True
                )

            # -----------------------------
            # VisitLog data below
            # -----------------------------
            st.markdown("---")
            st.markdown("## 📋 Complete VisitLog Details")

            if site_visits.empty:
                st.warning("No VisitLog records found for this selected site.")
            else:
                f1, f2, f3 = st.columns(3)

                with f1:
                    month_list = ["All"] + get_unique_values(site_visits, "Month")
                    selected_month_filter = st.selectbox(
                        "Filter by Month",
                        month_list,
                        key="site_card_month_filter"
                    )

                with f2:
                    status_list = ["All"] + get_unique_values(site_visits, "Status")
                    selected_status_filter = st.selectbox(
                        "Filter by Status",
                        status_list,
                        key="site_card_status_filter"
                    )

                with f3:
                    associate_col = get_first_col(site_visits, ["Associate ID", "Associate", "Technical Person"])
                    if associate_col:
                        associate_list = ["All"] + get_unique_values(site_visits, associate_col)
                    else:
                        associate_list = ["All"]

                    selected_associate_filter = st.selectbox(
                        "Filter by Associate",
                        associate_list,
                        key="site_card_associate_filter"
                    )

                site_log_filtered = site_visits.copy()

                if selected_month_filter != "All":
                    site_log_filtered = site_log_filtered[site_log_filtered["Month"] == selected_month_filter]

                if selected_status_filter != "All":
                    site_log_filtered = site_log_filtered[site_log_filtered["Status"] == selected_status_filter]

                if associate_col and selected_associate_filter != "All":
                    site_log_filtered = site_log_filtered[
                        site_log_filtered[associate_col].astype(str) == selected_associate_filter
                    ]

                # -----------------------------
                # Show important VisitLog columns first
                # -----------------------------
                important_visit_cols = [
                    "Source Sheet",
                    "Visit ID",
                    visit_site_col,
                    "Tower Name",
                    "FloorsVisited",
                    "Floors Visited",
                    "Associate ID",
                    "Date of Visit",
                    "Is Report Visit?",
                    "Status",
                    "Report Submitted Date",
                    "Comment",
                    "CreatedAt"
                ]

                final_visit_cols = []

                for col in important_visit_cols:
                    if col and col in site_log_filtered.columns and col not in final_visit_cols:
                        final_visit_cols.append(col)

                # Add remaining columns also, so no data is missed
                for col in site_log_filtered.columns:
                    if col not in final_visit_cols:
                        final_visit_cols.append(col)

                st.dataframe(
                    site_log_filtered[final_visit_cols].astype(str),
                    use_container_width=True,
                    hide_index=True
                )

                csv_data = site_log_filtered[final_visit_cols].to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="⬇️ Download This Site VisitLog",
                    data=csv_data,
                    file_name=f"{selected_site}_VisitLog.csv",
                    mime="text/csv"
                )
