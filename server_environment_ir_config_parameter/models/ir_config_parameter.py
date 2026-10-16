# Copyright 2016-2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.server_environment.server_env import serv_config

SECTION = "ir.config_parameter"


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    is_environment = fields.Boolean(
        string="Defined by environment",
        compute="_compute_is_environment",
        help="If check, the value in the database will be ignored"
        " and alternatively, the system will use the key defined"
        " in your odoo.cfg environment file.",
    )

    def _compute_is_environment(self):
        for parameter in self:
            parameter.is_environment = serv_config.has_option(SECTION, parameter.key)

    def _get(self, key, type_="str"):
        if self.env.context.get("_from_get_param"):
            # raw database access, used when (re)writing the parameter
            return super()._get(key, type_)
        if serv_config.has_option(SECTION, key):
            cvalue = serv_config.get(SECTION, key)
            if not cvalue:
                raise UserError(
                    self.env._("Key %s is empty in server_environment_file", key)
                )
            if cvalue != super()._get(key, "str")[0]:
                # we write in db on first access;
                # should we have preloaded values in database at,
                # server startup, modules loading their parameters
                # from data files would break on unique key error.
                self.sudo().set_str(key, cvalue)
        return super()._get(key, type_)

    def _set(self, key, value, type_):
        # the check is to avoid recursion: _set() reads the current value
        # with _get(), which must return the database value (the value
        # *before* the change) without synchronizing it from the config file
        return super(IrConfigParameter, self.with_context(_from_get_param=1))._set(
            key, value, type_
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            key = vals.get("key")
            if key and serv_config.has_option(SECTION, key):
                # enforce value from config file
                vals.update(value=serv_config.get(SECTION, key))
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            key = vals.get("key", rec.key)
            if serv_config.has_option(SECTION, key):
                # enforce value from config file
                newvals = dict(vals, value=serv_config.get(SECTION, key))
            else:
                newvals = vals
            super(IrConfigParameter, rec).write(newvals)
        return True
