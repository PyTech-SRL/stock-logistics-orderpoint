# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo.fields import Command
from odoo.tests import common


class TestStockOrderpointMtoAsMts(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.warehouse.write(
            {"archive_orderpoints_mto_removal": True, "mto_as_mts": True}
        )
        cls.warehouse1 = cls.env["stock.warehouse"].create(
            {
                "name": "Test Warehouse",
                "code": "TWH",
                "archive_orderpoints_mto_removal": True,
                "mto_as_mts": True,
            }
        )

        cls.mto_route = cls.env.ref("stock.route_warehouse0_mto")
        cls.mto_route.write(
            {
                "active": True,
                "is_mto": True,
            }
        )

    def test_orderpoint_with_product(self):
        # Create orderpoint
        product = self.env["product.product"].create(
            {
                "name": "Test MTO",
                "type": "product",
                "route_ids": [(6, 0, [self.mto_route.id])],
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 2)
        # Archive orderpoint
        product.write({"route_ids": [(6, 0, [])]})
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)

    def test_orderpoint_when_changing_company(self):
        # Create orderpoint
        product = self.env["product.product"].create(
            {
                "name": "Test MTO",
                "type": "product",
                "route_ids": [(6, 0, [self.mto_route.id])],
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 2)
        # Change company
        product.write(
            {"company_id": self.env["res.company"].create({"name": "New Company"}).id}
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)

    def test_orderpoint_when_changing_category_routes(self):
        category = self.env.ref("product.product_category_all")
        product = self.env["product.product"].create(
            {
                "name": "Test MTO",
                "type": "product",
                "categ_id": category.id,
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)
        self.env.invalidate_all()
        # Add MTO route on product category
        category.write({"route_ids": [(6, 0, [self.mto_route.id])]})
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 2)

    def test_orderpoint_when_changing_is_mto_on_routes(self):
        # Reset is MTO on route
        self.mto_route.is_mto = False
        category = self.env.ref("product.product_category_all")
        product = self.env["product.product"].create(
            {
                "name": "Test MTO",
                "type": "product",
                "categ_id": category.id,
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)
        # Check case: Enable is_mto on route that has been linked to product
        product.write({"route_ids": [(6, 0, [self.mto_route.id])]})
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)
        self.mto_route.is_mto = True  # Enable is_mto on route

        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 2)

        # Check case: Enable is_mto on route that has been linked to product category
        self.mto_route.is_mto = False  # Reset is MTO on route
        product.write({"route_ids": [(6, 0, [])]})  # Reset route on product
        self.env.invalidate_all()
        category.write(
            {
                "route_ids": [
                    (6, 0, [self.mto_route.id])  # Add route on product category
                ]
            }
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertFalse(orderpoint)
        # Enable is_mto on route
        self.mto_route.is_mto = True
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product.id)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 2)

    def test_orderpoint_with_template(self):
        # Create a template with 3 variants
        color_attribute = self.env["product.attribute"].create(
            {
                "name": "Color",
                "value_ids": [
                    Command.create({"name": "red", "sequence": 1}),
                    Command.create({"name": "blue", "sequence": 2}),
                    Command.create({"name": "green", "sequence": 3}),
                ],
            }
        )
        (
            color_attribute_red,
            color_attribute_blue,
            color_attribute_green,
        ) = color_attribute.value_ids
        product_template_sofa = self.env["product.template"].create(
            {
                "name": "Sofa",
                "type": "product",
                "route_ids": [(6, 0, [self.mto_route.id])],
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": color_attribute.id,
                            "value_ids": [
                                Command.set(
                                    [
                                        color_attribute_red.id,
                                        color_attribute_blue.id,
                                        color_attribute_green.id,
                                    ]
                                )
                            ],
                        }
                    )
                ],
            }
        )
        self.assertEqual(len(product_template_sofa.product_variant_ids), 3)
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "in", product_template_sofa.product_variant_ids.ids)]
        )
        self.assertTrue(orderpoint)
        self.assertTrue(len(orderpoint) == 6)
        # Archive orderpoint
        product_template_sofa.write({"route_ids": [(6, 0, [])]})
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "in", product_template_sofa.product_variant_ids.ids)]
        )
        self.assertFalse(orderpoint)
