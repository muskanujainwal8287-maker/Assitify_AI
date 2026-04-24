import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/docs/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const generateSummary = async (payload) => {
  const { data } = await api.post("/generate/summary", payload);
  return data;
};

export const generateQuestions = async (payload) => {
  const { data } = await api.post("/generate/questions", payload);
  return data;
};

export const reviewAnswers = async (payload) => {
  const { data } = await api.post("/test/review", payload);
  return data;
};
