import { useNavigate } from "react-router-dom";
import { createProject } from "../api/projects";
import ProjectForm from "../components/ProjectForm";
import { notifySuccess } from "../lib/toast";

export default function CreateProject() {
  const navigate = useNavigate();

  const handleSubmit = async (formData) => {
    const { data } = await createProject(formData);
    notifySuccess("تم نشر مشروعك بنجاح.");
    navigate(`/projects/${data.id}`);
  };

  return (
    <div>
      <div className="container" style={{ paddingTop: 40 }}>
        <h1 className="section-heading">ابدأ حملة جديدة</h1>
        <p style={{ color: "var(--ink-600)", marginTop: -14 }}>
          اكتب تفاصيل مشروعك بوضوح — كل حاجة تقدر تعدّلها بعدين.
        </p>
      </div>
      <ProjectForm onSubmit={handleSubmit} submitLabel="نشر المشروع" />
    </div>
  );
}
