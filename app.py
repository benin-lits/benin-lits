# DANS Dashboard, remplace tout le if menu == "Dashboard": par ceci:

if menu == "Dashboard":
    st.subheader(f"Dashboard - {centre_actuel}")
    
    df_ref_all = pd.read_sql("SELECT * FROM benin_refs", conn)
    df_lits = pd.read_sql("SELECT * FROM lits", conn)

    # ========== BLOC 1 : POINT GLOBAL (comme sur ta photo) ==========
    st.write("## 🌍 POINT GLOBAL - Tous centres, toutes dates")
    total_lits_g = df_lits["lits_total"].sum() if not df_lits.empty else 0
    total_occ_g = df_lits["lits_occupes"].sum() if not df_lits.empty else 0
    total_dispo_g = total_lits_g - total_occ_g
    taux_g = round((total_occ_g/total_lits_g*100) if total_lits_g>0 else 0,1)
    cumul_g = round(df_ref_all["distance_km"].sum() if not df_ref_all.empty else 0,1)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Réf", len(df_ref_all))
    c2.metric("Total Lits", total_lits_g)
    c3.metric("Lits Occupés", total_occ_g)
    c4.metric("Lits Dispo", total_dispo_g)
    c5.metric("Taux Occupation", f"{taux_g} %")
    c6.metric("Cumul Distance Total", f"{cumul_g} km")

    if not df_ref_all.empty:
        colA, colB = st.columns(2)
        with colA:
            st.write("### 🥧 Camembert Global - Motifs")
            motif_counts = df_ref_all["motif"].value_counts()
            fig, ax = plt.subplots()
            ax.pie(motif_counts, labels=motif_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        with colB:
            st.write("### 🛏️ Lits par Centre - Global")
            df_lits["lits_dispo"] = df_lits["lits_total"] - df_lits["lits_occupes"]
            st.dataframe(df_lits)
        
        st.write("### 📍 Cumul Distance Global par Centre")
        cumul_global = df_ref_all.groupby("centre_origine")["distance_km"].agg(['count','sum']).reset_index()
        cumul_global.columns = ["Centre", "Nb Réf", "Cumul km"]
        st.dataframe(cumul_global, use_container_width=True)

    st.divider()
    
    # ========== BLOC 2 : POINT FILTRE ==========
    st.write("## 🔍 POINT FILTRÉ - Par Date / Centre / Niveau")
    f1,f2,f3,f4,f5 = st.columns(5)
    with f1: date_debut = st.date_input("Du", datetime.now() - timedelta(days=30), key="f_debut")
    with f2: date_fin = st.date_input("Au", datetime.now(), key="f_fin")
    with f3: niveau = st.selectbox("Niveau", ["Tous", "CS", "CHD", "CNHU"], key="f_niv")
    with f4: centre_filtre = st.selectbox("Centre Origine", ["Tous"] + list(CENTRES.keys()), key="f_centre")
    with f5: dest_filtre = st.selectbox("Destination", ["Tous"] + [c for c in CENTRES if CENTRES[c]["type"]!="CS"], key="f_dest")
    
    raccourci = st.selectbox("Raccourci date", ["Personnalisé", "Aujourd'hui", "7 jours", "Ce mois", "Tout"], index=4)
    if raccourci == "Aujourd'hui": date_debut = date_fin = datetime.now().date()
    elif raccourci == "7 jours": date_debut = (datetime.now() - timedelta(days=7)).date()
    elif raccourci == "Ce mois": date_debut = datetime.now().replace(day=1).date()
    elif raccourci == "Tout": date_debut = datetime(2020,1,1).date()

    # Filtrage
    df_ref = df_ref_all.copy()
    if not df_ref.empty:
        df_ref['date_only'] = pd.to_datetime(df_ref['date']).dt.date
        df_ref = df_ref[(df_ref['date_only'] >= date_debut) & (df_ref['date_only'] <= date_fin)]
        if niveau != "Tous":
            centres_niveau = [k for k,v in CENTRES.items() if v["type"]==niveau]
            df_ref = df_ref[df_ref['centre_origine'].isin(centres_niveau) | df_ref['centre_dest'].isin(centres_niveau)]
        if centre_filtre != "Tous": df_ref = df_ref[df_ref['centre_origine']==centre_filtre]
        if dest_filtre != "Tous": df_ref = df_ref[df_ref['centre_dest']==dest_filtre]

    st.info(f"Filtré: {date_debut} au {date_fin} | Niveau: {niveau} | Origine: {centre_filtre} -> {len(df_ref)} ref(s) | Cumul: {round(df_ref['distance_km'].sum(),1) if not df_ref.empty else 0} km")
    
    if not df_ref.empty:
        c1,c2,c3 = st.columns(3)
        c1.metric("Réf Filtrées", len(df_ref))
        c2.metric("Cumul Distance Filtré", f"{round(df_ref['distance_km'].sum(),1)} km")
        c3.metric("Moyenne Distance", f"{round(df_ref['distance_km'].mean(),1)} km")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("#### Camembert Filtré")
            mc = df_ref["motif"].value_counts()
            fig2, ax2 = plt.subplots(); ax2.pie(mc, labels=mc.index, autopct='%1.1f%%'); ax2.axis('equal'); st.pyplot(fig2)
        with col2:
            st.write("#### Cumul par Centre Filtré")
            cumul_f = df_ref.groupby("centre_origine")["distance_km"].agg(['count','sum']).reset_index()
            cumul_f.columns = ["Centre", "Nb", "Cumul km"]; st.dataframe(cumul_f)
            st.bar_chart(cumul_f.set_index("Centre")["Cumul km"])

        # Export
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_ref.to_excel(writer, sheet_name='Filtre', index=False)
            cumul_global.to_excel(writer, sheet_name='Global', index=False)
        st.download_button("📥 Export Excel (Point Filtré)", buffer.getvalue(), file_name=f"benin_lits_{niveau}_{date_debut}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(df_ref.sort_values("date", ascending=False))
