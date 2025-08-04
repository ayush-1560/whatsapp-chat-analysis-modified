    with st.expander("📁 Media Files Summary"):
                counts = Counter([os.path.splitext(f)[1].lower() for f in media_files])
                st.write("**Media Types and Counts:**")
                for ext, count in counts.items():
                    st.write(f"- `{ext}` → {count} files")
                st.write("**Example Media Files:**")
                st.write(media_files[:10])

        st.markdown("<br>", unsafe_allow_html=True)