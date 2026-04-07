import { useEffect, useState } from "react";
import axios from "axios";
import { Table, Select, Row, Col, Card } from "antd";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const { Option } = Select;

interface UnidadMedica {
  clave: string;
  region: string;
  delegacion: string;
  nivel: string;
  unidad: string;
}

export const DashboardAntD = () => {
  const [UnidadesMedicas, setUnidadesMedicas] = useState<UnidadMedica[]>([]);
  const [regionSeleccionada, setRegionSeleccionada] = useState<
    string | undefined
  >();
  const [delegacionSeleccionada, setDelegacionSeleccionada] = useState<
    string | undefined
  >();

  // Obtener datos del backend
  useEffect(() => {
    axios
      .get<UnidadMedica[]>("http://localhost:8000/api/usuarios/")
      .then((res) => setUnidadesMedicas(res.data))
      .catch((err) => console.error("Error al cargar unidades médicas:", err));
  }, []);

  // Filtrar opciones únicas
  const regionesUnicas = [...new Set(UnidadesMedicas.map((u) => u.region))];
  const delegacionesUnicas = [
    ...new Set(
      UnidadesMedicas.filter(
        (u) => !regionSeleccionada || u.region === regionSeleccionada
      ).map((u) => u.delegacion)
    ),
  ];

  // Filtrar tabladdd
  const UniMedFiltrados = UnidadesMedicas.filter((u) => {
    return (
      (!regionSeleccionada || u.region === regionSeleccionada) &&
      (!delegacionSeleccionada || u.delegacion === delegacionSeleccionada)
    );
  });

  // Datos para la gráfica
  const conteoPorDelegacion = UniMedFiltrados.reduce(
    (acc: Record<string, number>, u) => {
      acc[u.delegacion] = (acc[u.delegacion] || 0) + 1;
      return acc;
    },
    {}
  );

  const dataGrafica = Object.entries(conteoPorDelegacion).map(
    ([delegacion, total]) => ({
      delegacion,
      total,
    })
  );

  return (
    <div style={{ padding: "24px" }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Select
            allowClear
            style={{ width: "100%" }}
            placeholder="Selecciona Región"
            onChange={(value) => {
              setRegionSeleccionada(value);
              setDelegacionSeleccionada(undefined); // Reiniciar delegación si cambia región
            }}
            value={regionSeleccionada}
          >
            {regionesUnicas.map((region) => (
              <Option key={region} value={region}>
                {region}
              </Option>
            ))}
          </Select>
        </Col>

        <Col span={6}>
          <Select
            allowClear
            style={{ width: "100%" }}
            placeholder="Selecciona Delegación"
            onChange={setDelegacionSeleccionada}
            value={delegacionSeleccionada}
            disabled={!regionSeleccionada}
          >
            {delegacionesUnicas.map((delegacion) => (
              <Option key={delegacion} value={delegacion}>
                {delegacion}
              </Option>
            ))}
          </Select>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: "24px" }}>
        <Col span={12}>
          <Card title="Unidades Médicas por Delegación">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dataGrafica}>
                <XAxis dataKey="delegacion" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total" fill="#1890ff" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col span={12}>
          <Card title="Unidades Médicas por Delegación">
            <Table
              dataSource={UniMedFiltrados}
              rowKey="clave"
              pagination={{ pageSize: 5 }}
              columns={[
                { title: "Clave", dataIndex: "clave" },
                { title: "Región", dataIndex: "region" },
                { title: "Delegación", dataIndex: "delegacion" },
                { title: "Nivel", dataIndex: "nivel" },
                { title: "Unidad", dataIndex: "unidad" },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};
