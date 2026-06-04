import { Layout, Typography, Button, Space } from 'antd';
import { Outlet, Link } from 'react-router-dom';

const { Header, Content } = Layout;

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ color: '#fff', margin: 0 }}>
          SolidiGuard
        </Typography.Title>
        <Space style={{ marginLeft: 'auto' }}>
          <Link to="/upload">
            <Button type="text" style={{ color: '#fff' }}>Upload</Button>
          </Link>
          <Link to="/vulnerabilities">
            <Button type="text" style={{ color: '#fff' }}>Vulnerability DB</Button>
          </Link>
        </Space>
      </Header>
      <Content style={{ padding: '24px' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
